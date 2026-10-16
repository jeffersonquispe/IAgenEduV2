"""HU-34: límite compartido de llamadas a Bedrock en vuelo."""
import json
import threading
import time
from unittest.mock import MagicMock

import pytest

from src.core import bedrock_client as bc
from src.core.bedrock_client import BedrockClient, LimiteConcurrencia


@pytest.fixture
def limite(monkeypatch):
    """Límite de 2 aislado por test (no toca el singleton real del proceso)."""
    lim = LimiteConcurrencia(2)
    monkeypatch.setattr(bc, "_limite", lim)
    return lim


class ClienteFalso:
    """Registra cuántas invocaciones coinciden en el tiempo."""

    def __init__(self, demora=0.05, falla=False):
        self.demora, self.falla = demora, falla
        self._lock = threading.Lock()
        self.actual = 0
        self.maximo = 0
        self.llamadas = 0

    def invoke_model(self, **_):
        with self._lock:
            self.actual += 1
            self.llamadas += 1
            self.maximo = max(self.maximo, self.actual)
        try:
            time.sleep(self.demora)
            if self.falla:
                raise RuntimeError("boom")
            cuerpo = MagicMock()
            cuerpo.read.return_value = json.dumps({"content": [{"text": "x" * 100}]})
            return {"body": cuerpo}
        finally:
            with self._lock:
                self.actual -= 1


def _cliente(falso) -> BedrockClient:
    c = BedrockClient(max_reintentos=1)
    c._client = falso
    return c


# --- LimiteConcurrencia ---

def test_limite_nunca_excede_el_maximo_con_muchos_hilos(limite):
    falso = ClienteFalso()
    cliente = _cliente(falso)
    hilos = [threading.Thread(target=cliente.invocar, args=("p",)) for _ in range(10)]
    [h.start() for h in hilos]
    [h.join(timeout=10) for h in hilos]
    assert falso.llamadas == 10                  # todas se atienden (esperan en cola)
    assert falso.maximo <= 2                     # pero nunca más de 2 a la vez
    assert falso.maximo == 2                     # y sí se aprovecha el cupo
    assert limite.en_vuelo == 0 and limite.esperando == 0


def test_slot_se_libera_si_la_llamada_falla(limite):
    cliente = _cliente(ClienteFalso(falla=True))
    for _ in range(5):                           # más fallos que el cupo: si no se liberara, se colgaría
        with pytest.raises(RuntimeError):
            cliente.invocar("p")
    assert limite.en_vuelo == 0


def test_llamadas_en_exceso_esperan_y_se_reportan(limite):
    liberar = threading.Event()
    entraron = []

    def ocupar():
        with limite:
            entraron.append(1)
            liberar.wait(5)

    ocupantes = [threading.Thread(target=ocupar) for _ in range(2)]
    [t.start() for t in ocupantes]
    while len(entraron) < 2:
        time.sleep(0.01)
    tercero = threading.Thread(target=lambda: limite.__enter__() and limite.__exit__())
    tercero.start()
    time.sleep(0.1)
    assert limite.esperando == 1 and limite.en_vuelo == 2     # el tercero está en cola
    liberar.set()
    [t.join(timeout=5) for t in ocupantes + [tercero]]
    assert limite.esperando == 0 and limite.en_vuelo == 0


# --- Streaming ---

def _stream_falso(n_chunks=3):
    evento = {"chunk": {"bytes": json.dumps(
        {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "a"}}).encode()}}
    falso = MagicMock()
    falso.invoke_model_with_response_stream.return_value = {"body": iter([evento] * n_chunks)}
    return falso


def test_stream_ocupa_slot_mientras_dura_y_lo_libera_al_terminar(limite):
    cliente = _cliente(_stream_falso())
    gen = cliente.invocar_stream("p")
    assert limite.en_vuelo == 0                  # un generador sin iterar no retiene cupo
    assert next(gen) == "a"
    assert limite.en_vuelo == 1                  # en vuelo mientras hay stream abierto
    assert list(gen) == ["a", "a"]
    assert limite.en_vuelo == 0


def test_stream_libera_el_slot_si_el_consumidor_lo_cierra_a_la_mitad(limite):
    cliente = _cliente(_stream_falso())
    gen = cliente.invocar_stream("p")
    next(gen)
    assert limite.en_vuelo == 1
    gen.close()                                  # p. ej. el navegador cortó la conexión SSE
    assert limite.en_vuelo == 0


def test_streams_concurrentes_respetan_el_limite(limite):
    maximo, actual, lock = [0], [0], threading.Lock()

    def consumir():
        falso = MagicMock()

        def lento():
            for _ in range(3):
                time.sleep(0.03)
                yield {"chunk": {"bytes": json.dumps(
                    {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "a"}}).encode()}}
        falso.invoke_model_with_response_stream.return_value = {"body": lento()}
        c = _cliente(falso)
        for i, _ in enumerate(c.invocar_stream("p")):
            with lock:
                if i == 0:
                    actual[0] += 1
                    maximo[0] = max(maximo[0], actual[0])
        with lock:
            actual[0] -= 1

    hilos = [threading.Thread(target=consumir) for _ in range(6)]
    [h.start() for h in hilos]
    [h.join(timeout=10) for h in hilos]
    assert maximo[0] <= 2 and limite.en_vuelo == 0


# --- Configuración ---

@pytest.mark.parametrize("valor,esperado", [
    (None, bc.DEFAULT_BEDROCK_MAX_CONCURRENCY),
    ("", bc.DEFAULT_BEDROCK_MAX_CONCURRENCY),
    ("7", 7),
    (" 3 ", 3),
    ("0", bc.DEFAULT_BEDROCK_MAX_CONCURRENCY),
    ("-2", bc.DEFAULT_BEDROCK_MAX_CONCURRENCY),
    ("muchos", bc.DEFAULT_BEDROCK_MAX_CONCURRENCY),
])
def test_lectura_de_variable_de_entorno(monkeypatch, valor, esperado):
    if valor is None:
        monkeypatch.delenv("BEDROCK_MAX_CONCURRENCY", raising=False)
    else:
        monkeypatch.setenv("BEDROCK_MAX_CONCURRENCY", valor)
    assert bc._leer_max_concurrencia() == esperado


def test_el_limite_del_proceso_es_unico_y_toma_el_entorno(monkeypatch):
    monkeypatch.setattr(bc, "_limite", None)
    monkeypatch.setenv("BEDROCK_MAX_CONCURRENCY", "5")
    a = bc.get_limite_concurrencia()
    assert a is bc.get_limite_concurrencia() and a.maximo == 5
    monkeypatch.setattr(bc, "_limite", None)       # no dejar un límite de 5 para otros tests


def test_el_default_es_conservador():
    assert 1 <= bc.DEFAULT_BEDROCK_MAX_CONCURRENCY <= 5
