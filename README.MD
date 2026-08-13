# Credit Risk MLOps — Pipeline End-to-End en AWS

Sistema completo de scoring de riesgo crediticio, construido para demostrar el ciclo de vida completo de un proyecto de MLOps en producción: desde la ingesta de datos hasta el monitoreo y reentrenamiento automático del modelo.

**Problema de negocio:** predecir la probabilidad de que un solicitante de crédito incurra en default (impago), usando datos de la solicitud e historial crediticio externo.

**Dataset:** [Home Credit Default Risk](https://www.kaggle.com/competitions/home-credit-default-risk) (Kaggle) — 307,511 solicitudes de crédito, tasa de default del 8.07%.

**Por qué este proyecto:** más allá de entrenar un modelo con buen desempeño, el objetivo fue construir la infraestructura completa que rodea a un modelo en producción real — algo que la mayoría de proyectos de portafolio de ML omiten. Cada componente está desplegado, probado y documentado con datos y resultados reales, no simulados.

---

## Arquitectura

```
Kaggle (raw data)
      │
      ▼
   S3 (raw/)
      │
      ▼
  AWS Glue ETL (arquitectura Medallion: Bronze → Silver → Gold)
      │
      ▼
  SageMaker Pipeline
  (preprocesamiento → entrenamiento XGBoost → evaluación → registro condicional)
      │
      ▼
  Model Registry (aprobación manual)
      │
      ├──────────────────────────┬──────────────────────────────────┐
      ▼                          ▼                                  │
  Camino A                   Camino B                                │
  SageMaker Endpoint         FastAPI + Docker → ECR → ECS Fargate    │
  (tiempo real, nativo)      → API Gateway (HTTP API)                │
      │                          │                                  │
      └──────────────┬───────────┘                                  │
                      ▼                                              │
              A/B Testing (latencia + consistencia de predicciones)  │
                      │                                              │
                      ▼                                              │
     Monitoreo: Data Capture + baseline estadístico + detección      │
     de drift (script custom, ver sección Monitoreo)                 │
                      │                                              │
                      ▼                                              │
     EventBridge (diario) → Lambda → si hay drift → dispara ──────────┘
     reentrenamiento automático del SageMaker Pipeline

Toda la infraestructura: Terraform (modular, por servicio)
CI: GitHub Actions (validación automática en cada push)
CD: GitHub Actions (terraform apply con aprobación manual — diseñado, no activado)
```

### Arquitectura de datos: Medallion (Bronze / Silver / Gold)

Implementada con dos AWS Glue Jobs independientes, orquestados por Terraform:

- **Bronze → Silver** (`bronze_to_silver.py`): limpia `application_train.csv` (elimina columnas sin señal predictiva basándose en evidencia, no en umbrales arbitrarios; imputa valores faltantes con justificación documentada) y agrega `bureau.csv` (1.7M filas) a nivel de cliente.
- **Silver → Gold** (`silver_to_gold.py`): une ambas tablas Silver, agrega el flag `BUREAU_HISTORY_MISSING`, y escribe el dataset final listo para entrenamiento en `processed/`.

Esta separación permite reutilizar cada tabla limpia de forma independiente y mantiene cada Glue Job enfocado en una sola responsabilidad.

---

## Decisiones técnicas clave

### Valores faltantes y selección de columnas
Cada columna con missingness significativo fue evaluada por señal predictiva real (correlación con `TARGET` en numéricas, delta de tasa de default por categoría en categóricas) antes de decidir descartarla, imputarla o conservarla — no se usó un umbral arbitrario de "% de nulos". Resultado: 51 columnas descartadas con evidencia, 3 columnas imputadas y conservadas con flags de missingness (`EXT_SOURCE_1_MISSING`, `EXT_SOURCE_3_MISSING`, `BUREAU_HISTORY_MISSING`).

### Categorías raras
Categorías con menos del 1% de representación en `ORGANIZATION_TYPE` se agruparon en `"Other"` antes del one-hot encoding, evitando columnas dummy con señal estadística débil.

### Desbalance de clases
Manejado vía `scale_pos_weight ≈ 11.39` en XGBoost (basado en la proporción real 91.9% / 8.07%), en vez de resampling — evita introducir datos sintéticos y preserva la distribución real durante la evaluación.

### Umbral de decisión
Fijado en 0.5, priorizando explícitamente **recall (67%)** sobre **precisión (16.8%)** — en riesgo crediticio, el costo de no detectar un default real es mayor que el de una revisión manual adicional. Es una decisión de negocio deliberada y documentada, no un valor por defecto sin examinar.

### Governance del modelo
El SageMaker Pipeline registra el modelo en el Model Registry únicamente si supera un umbral de AUC ≥ 0.70 (`ConditionStep`), y requiere **aprobación manual** antes de que cualquier modelo pueda desplegarse — ningún modelo llega a producción sin revisión humana explícita.

**AUC logrado en el pipeline productivo: 0.7567**

---

## Doble camino de despliegue (Camino A vs. Camino B)

Un mismo modelo aprobado, servido de dos formas arquitectónicamente distintas — para comparar un servicio administrado de AWS contra una solución construida desde cero.

### Camino A — SageMaker Endpoint (nativo, tiempo real)
Despliegue directo desde el Model Registry vía el SDK de SageMaker (`ModelPackage.deploy()`). AWS gestiona el contenedor de inferencia, el escalado y la infraestructura subyacente por completo.

### Camino B — Microservicio propio
Construido pieza por pieza para demostrar control total sobre el stack de serving:
- **FastAPI** — endpoints `/predict` y `/health`, validación de entrada/salida con Pydantic, carga del modelo desde S3 una sola vez al arrancar (patrón `lifespan`)
- **Docker** — imagen `python:3.11-slim`, construida y probada localmente antes de tocar AWS
- **ECR** — registro privado de imágenes (tags inmutables, cifrado KMS, escaneo de vulnerabilidades activo)
- **ECS Fargate** — contenedor corriendo sin gestión de servidores, en subred pública (decisión consciente de costo, ver sección *Gestión de costos*)
- **API Gateway (HTTP API)** — URL pública estable y con HTTPS, integración tipo proxy hacia la tarea de ECS mediante una ruta catch-all (`ANY /{proxy+}`), sin Load Balancer ni VPC Link (costo cero)

Toda esta infraestructura está definida como código en Terraform, modular por servicio.

### Resultados del A/B Testing

Diez predicciones idénticas enviadas a ambos caminos simultáneamente:

| Métrica | SageMaker Endpoint | ECS + API Gateway |
|---|---|---|
| Coincidencia de resultados | 10/10 exactos | 10/10 exactos |
| Latencia promedio | 195.7 ms | 662.2 ms |

**Conclusión:** ambos caminos producen predicciones numéricamente idénticas, confirmando la consistencia del modelo servido. SageMaker resultó ~3.4x más rápido en esta prueba — esperable, dado que evita el salto de red adicional de API Gateway y usa un protocolo interno optimizado de AWS en vez de un servidor HTTP genérico (Uvicorn). El Camino B, a cambio, ofrece control total del código de serving y portabilidad fuera del ecosistema SageMaker.

---

## Monitoreo y detección de drift

### Contexto importante
SageMaker Model Monitor (el servicio nativo de AWS para este propósito) **dejó de estar disponible para cuentas nuevas de AWS desde el 30 de julio de 2026** — una restricción real de la plataforma, no un límite de este proyecto. En vez de omitir esta fase, se construyó una solución equivalente:

### Solución implementada
1. **Baseline estadístico** — generado a partir del dataset de entrenamiento real (reconstruido con nombres de columna reales desde los archivos Parquet de origen, replicando exactamente la lógica de `preprocess.py`), usando `suggest_baseline` del SDK de SageMaker (esta función sí sigue disponible).
2. **Data Capture** — activado en el Endpoint de SageMaker, registrando cada predicción real (input y output) en S3.
3. **Script de detección de drift custom** (`check_drift.py`) — compara la media de cada columna numérica de los datos capturados recientemente contra el baseline, usando z-score. Columnas con desviación mayor a 3 desviaciones estándar se marcan como posible drift.

### Validación con datos reales
- **Sin drift** (tráfico normal): 0/190 columnas marcadas — confirma ausencia de falsos positivos.
- **Con drift simulado** (montos de crédito multiplicados x5, simulando un cambio real de segmento de clientes): el sistema detectó correctamente `AMT_CREDIT` con **z-score = 6.67** — muy por encima del umbral, confirmando que el mecanismo de detección funciona de punta a punta con datos reales, no solo en teoría.

---

## Automatización

El ciclo de vida completo se cierra con **AWS Lambda + EventBridge**, ambos desplegados vía Terraform:

- **EventBridge** — regla programada (`rate(1 day)`), simulando el schedule que tendría en un entorno de producción 24/7.
- **Lambda** (`check_drift_lambda.py`) — reescritura sin dependencias externas (solo `boto3`, `json`, `statistics` — módulos nativos de Python, por límites de tamaño de paquete en Lambda) de la lógica de detección de drift. Si detecta drift, dispara automáticamente una nueva ejecución del SageMaker Pipeline (`sagemaker:StartPipelineExecution`) — sin intervención manual.
- **Salvaguarda de frescura** — la Lambda ignora datos capturados con más de 2 horas de antigüedad, evitando disparos por datos obsoletos de pruebas anteriores (una salvaguarda añadida tras un disparo real accidental durante el desarrollo — ver sección *Retos técnicos reales*).

---

## CI/CD

Implementado con GitHub Actions, con una separación deliberada entre validación e implementación:

- **CI (`ci.yml`)** — se ejecuta automáticamente en cada push: valida formato y sintaxis de Terraform (`terraform fmt`, `terraform validate`, sin credenciales de AWS) y confirma que la imagen Docker del microservicio sigue construyendo correctamente.
- **CD (`cd.yml`)** — disparo manual (`workflow_dispatch`), con `terraform plan` automático seguido de `terraform apply` protegido por un *GitHub Environment* que requiere aprobación manual explícita antes de ejecutarse.

**Nota de diseño:** el workflow de CD está completo y documentado en el repositorio, pero **no se conectó con credenciales reales de AWS** — es una decisión deliberada para un proyecto de portafolio (no de producción), evitando cualquier riesgo de aplicar cambios no revisados en una cuenta personal.

---

## Gestión de costos

Todo el proyecto se desarrolló bajo una restricción explícita: **cero gasto en AWS más allá de la capa gratuita**. Esto influyó directamente en varias decisiones de arquitectura:

- ECS Fargate en **subred pública**, sin NAT Gateway ni Load Balancer (ambos con costo fijo mensual)
- API Gateway HTTP API en vez de REST API (más económico, con free tier de 1M peticiones/mes)
- SageMaker Endpoint y tarea de ECS **apagados entre pruebas** (`delete-endpoint` / `desired_count = 0`), encendidos únicamente durante validaciones activas
- `desired_count` de ECS parametrizado en Terraform con valor por defecto `0`, para que la infraestructura nunca se reactive por accidente en un `apply` futuro

---

## Retos técnicos reales

Documentados con honestidad porque reflejan el proceso real de construcción, no solo el resultado final:

- **Cierre de SageMaker Model Monitor a cuentas nuevas** — descubierto en producción, resuelto con una solución custom equivalente (ver *Monitoreo*).
- **Disparo accidental de reentrenamiento real** — una prueba local de la Lambda de drift encontró datos de una sesión de prueba anterior y disparó una ejecución real del pipeline; se detuvo manualmente y se corrigió agregando una salvaguarda de frescura de datos.
- **Discrepancias de plataforma** — comportamiento de continuación de línea (`` ` `` vs `\`) y manejo de pipes en PowerShell vs. bash, resueltos adaptando los comandos.
- **Rutas de artefactos de SageMaker** — los outputs de `ProcessingStep` sin `destination` explícito se escriben al bucket por defecto de SageMaker, no al bucket propio del proyecto — localizado y documentado para la generación del baseline de monitoreo.

---

## Stack tecnológico

| Categoría | Herramientas |
|---|---|
| Procesamiento de datos | AWS Glue, PySpark, arquitectura Medallion |
| Almacenamiento | Amazon S3 (versionado, cifrado, bloqueo de acceso público) |
| Entrenamiento y MLOps | SageMaker Pipelines, Model Registry, XGBoost |
| Serving | SageMaker Endpoints, FastAPI, Docker, ECR, ECS Fargate, API Gateway |
| Monitoreo | Data Capture, detección de drift custom, CloudWatch |
| Automatización | AWS Lambda, EventBridge |
| Infraestructura como código | Terraform (modular por servicio) |
| CI/CD | GitHub Actions |

---

## Estructura del repositorio

```
credit-risk-mlops/
├── glue-scripts/          # ETL Bronze→Silver→Gold (PySpark)
├── sagemaker-pipeline/    # Pipeline de entrenamiento, despliegue, monitoreo
├── serving-api/           # Microservicio FastAPI (Camino B)
├── lambda/                # Función Lambda de detección de drift
├── terraform/             # Infraestructura como código, modular
│   ├── modules/            # s3, iam, glue, sagemaker, ecr, ecs, api_gateway,
│   │                        # lambda-drift-check, eventbridge
│   └── environments/dev/   # Configuración del entorno
└── .github/workflows/     # CI (automático) y CD (manual con aprobación)
```

---

## Estado del proyecto

- [x] Ingesta y limpieza de datos (Glue, arquitectura Medallion)
- [x] Pipeline de entrenamiento automatizado (SageMaker Pipelines + Model Registry)
- [x] Despliegue dual: SageMaker Endpoint (Camino A) + FastAPI/Docker/ECS (Camino B)
- [x] A/B Testing entre ambos caminos de despliegue
- [x] Monitoreo y detección de drift (validado con datos reales)
- [x] Automatización de reentrenamiento (Lambda + EventBridge)
- [x] Infraestructura completa como código (Terraform)
- [x] CI/CD con GitHub Actions

## Trabajo futuro

- Activar el CD real con credenciales de AWS en un entorno dedicado, fuera de la cuenta personal de portafolio
- Ampliar el detector de drift para variables categóricas (actualmente cubre las numéricas continuas)
- Incorporar tablas relacionales adicionales del dataset (`previous_application.csv`, `POS_CASH_balance.csv`) para explorar ganancias marginales de feature engineering

---

## Autor

**Ali Alejandro Guerrero Jaimes** — Data Engineer / AI-ML Engineer
[GitHub](https://github.com/aliguerreroj)