# =============================================================================
# SOLUCIÓN COMPLETA PARA ERROR 403 FORBIDDEN EN BEDROCK KNOWLEDGE BASE
# =============================================================================

# 1. CREAR COLECCIÓN OPENSEARCH SERVERLESS
echo "=== PASO 1: Crear colección OpenSearch Serverless ==="

# Crear encryption policy
aws opensearchserverless create-security-policy \
  --name "curriculo-encryption-policy" \
  --type "encryption" \
  --policy '{
    "Rules": [
      {
        "ResourceType": "collection",
        "Resource": ["collection/curriculo-nacional-peru"]
      }
    ],
    "AWSOwnedKey": true
  }'

# Crear network policy
aws opensearchserverless create-security-policy \
  --name "curriculo-network-policy" \
  --type "network" \
  --policy '[
    {
      "Rules": [
        {
          "ResourceType": "collection",
          "Resource": ["collection/curriculo-nacional-peru"]
        },
        {
          "ResourceType": "dashboard",
          "Resource": ["collection/curriculo-nacional-peru"]
        }
      ],
      "AllowFromPublic": true
    }
  ]'

# Crear data access policy
aws opensearchserverless create-access-policy \
  --name "curriculo-data-access-policy" \
  --type "data" \
  --policy '[
    {
      "Rules": [
        {
          "ResourceType": "index",
          "Resource": ["index/curriculo-nacional-peru/*"],
          "Permission": ["aoss:*"]
        },
        {
          "ResourceType": "collection",
          "Resource": ["collection/curriculo-nacional-peru"],
          "Permission": ["aoss:*"]
        }
      ],
      "Principal": [
        "arn:aws:iam::183150676819:role/BedrockKBRole"
      ]
    }
  ]'

# Crear la colección
aws opensearchserverless create-collection \
  --name "curriculo-nacional-peru" \
  --type "VECTORSEARCH" \
  --description "Documentos educativos MINEDU Peru"

echo "✅ Colección OpenSearch Serverless creada"
echo "⏳ Esperando que la colección esté activa (puede tomar 5-10 minutos)..."

# Esperar hasta que la colección esté activa
while true; do
  STATUS=$(aws opensearchserverless list-collections --query 'collectionSummaries[?name==`curriculo-nacional-peru`].status' --output text)
  if [ "$STATUS" = "ACTIVE" ]; then
    echo "✅ Colección activa"
    break
  else
    echo "⏳ Estado actual: $STATUS - Esperando..."
    sleep 30
  fi
done

# Obtener el endpoint de la colección
COLLECTION_ENDPOINT=$(aws opensearchserverless list-collections \
  --query 'collectionSummaries[?name==`curriculo-nacional-peru`].collectionEndpoint' \
  --output text)

echo "📍 Endpoint de colección: $COLLECTION_ENDPOINT"

# =============================================================================
# 2. ACTUALIZAR ROL IAM CON PERMISOS COMPLETOS
# =============================================================================
echo "=== PASO 2: Actualizar permisos del rol IAM ==="

# Crear política actualizada para el rol
cat > bedrock-kb-complete-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket",
        "s3:GetBucketLocation",
        "s3:GetBucketNotification",
        "s3:ListBucketMultipartUploads",
        "s3:ListBucketVersions"
      ],
      "Resource": [
        "arn:aws:s3:::minedu-educacion-peru",
        "arn:aws:s3:::minedu-educacion-peru/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v1",
        "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v2"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "aoss:APIAccessAll",
        "aoss:DashboardsAccessAll",
        "aoss:CreateCollectionItems",
        "aoss:DeleteCollectionItems",
        "aoss:UpdateCollectionItems",
        "aoss:DescribeCollectionItems"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:183150676819:log-group:/aws/bedrock/*"
    }
  ]
}
EOF

# Actualizar la política del rol
aws iam put-role-policy \
  --role-name BedrockKBRole \
  --policy-name BedrockKBCompletePolicy \
  --policy-document file://bedrock-kb-complete-policy.json

echo "✅ Permisos del rol actualizados"

# =============================================================================
# 3. CREAR ARCHIVOS DE CONFIGURACIÓN CORRECTOS
# =============================================================================
echo "=== PASO 3: Crear archivos de configuración ==="

# Archivo kb-config.json (configuración de la Knowledge Base)
cat > kb-config.json << 'EOF'
{
  "type": "VECTOR",
  "vectorKnowledgeBaseConfiguration": {
    "embeddingModelArn": "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1",
    "embeddingModelConfiguration": {
      "bedrockEmbeddingModelConfiguration": {
        "dimensions": 1536
      }
    }
  }
}
EOF

# Archivo storage-config.json (configuración de almacenamiento)
cat > storage-config.json << EOF
{
  "type": "OPENSEARCH_SERVERLESS",
  "opensearchServerlessConfiguration": {
    "collectionArn": "arn:aws:aoss:us-east-1:183150676819:collection/curriculo-nacional-peru",
    "vectorIndexName": "bedrock-knowledge-base-default-index",
    "fieldMapping": {
      "vectorField": "bedrock-knowledge-base-default-vector",
      "textField": "AMAZON_BEDROCK_TEXT_CHUNK",
      "metadataField": "AMAZON_BEDROCK_METADATA"
    }
  }
}
EOF

echo "✅ Archivos de configuración creados"

# =============================================================================
# 4. CREAR KNOWLEDGE BASE CON CONFIGURACIÓN CORRECTA
# =============================================================================
echo "=== PASO 4: Crear Knowledge Base ==="

aws bedrock-agent create-knowledge-base \
  --name "CurriculoNacionalPeru" \
  --role-arn "arn:aws:iam::183150676819:role/BedrockKBRole" \
  --knowledge-base-configuration file://kb-config.json \
  --storage-configuration file://storage-config.json

echo "✅ Knowledge Base creada exitosamente"

# =============================================================================
# 5. VERIFICAR CREACIÓN Y OBTENER IDs
# =============================================================================
echo "=== PASO 5: Verificar y obtener información ==="

# Listar Knowledge Bases para confirmar creación
aws bedrock-agent list-knowledge-bases --query 'knowledgeBaseSummaries[?name==`CurriculoNacionalPeru`]'

# Obtener detalles completos
KB_ID=$(aws bedrock-agent list-knowledge-bases \
  --query 'knowledgeBaseSummaries[?name==`CurriculoNacionalPeru`].knowledgeBaseId' \
  --output text)

echo "📋 Knowledge Base ID: $KB_ID"
echo "💾 Guarda este ID para usar en tu código Python"

# =============================================================================
# 6. SCRIPT DE LIMPIEZA (EN CASO DE ERRORES)
# =============================================================================
cat > cleanup.sh << 'EOF'
#!/bin/bash
echo "🧹 Script de limpieza - Ejecutar solo si hay errores"

# Eliminar Knowledge Base
KB_ID=$(aws bedrock-agent list-knowledge-bases --query 'knowledgeBaseSummaries[?name==`CurriculoNacionalPeru`].knowledgeBaseId' --output text)
if [ ! -z "$KB_ID" ]; then
  aws bedrock-agent delete-knowledge-base --knowledge-base-id "$KB_ID"
fi

# Eliminar colección OpenSearch
aws opensearchserverless delete-collection --id "curriculo-nacional-peru"

# Eliminar políticas de seguridad
aws opensearchserverless delete-security-policy --name "curriculo-encryption-policy" --type "encryption"
aws opensearchserverless delete-security-policy --name "curriculo-network-policy" --type "network" 
aws opensearchserverless delete-access-policy --name "curriculo-data-access-policy" --type "data"

echo "✅ Limpieza completada"
EOF

chmod +x cleanup.sh

echo "=================================="
echo "🎉 CONFIGURACIÓN COMPLETADA"
echo "=================================="
echo "📋 Knowledge Base ID: $KB_ID"
echo "📍 Collection Endpoint: $COLLECTION_ENDPOINT"
echo "🔧 Archivos generados:"
echo "   - kb-config.json"
echo "   - storage-config.json" 
echo "   - bedrock-kb-complete-policy.json"
echo "   - cleanup.sh"
echo ""
echo "📝 PRÓXIMOS PASOS:"
echo "1. Crear Data Source para conectar S3"
echo "2. Subir documentos del MINEDU a S3"
echo "3. Ejecutar sincronización"
echo "4. Probar consultas"
echo ""
echo "❌ Si hay errores, ejecutar: ./cleanup.sh"