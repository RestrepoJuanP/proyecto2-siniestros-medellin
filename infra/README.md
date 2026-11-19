# Infraestructura base

## Objetivo

Verificar el entorno local frente al AWS Academy Learner Lab y crear/destruir el bucket único del data lake con sus zonas (`raw/`, `trusted/`, `refined/`, `scripts/`, `athena-resultados/`).

## Cómo reproducir

Requisitos: credenciales del Learner Lab en `~/.aws/credentials`, región `us-east-1` y `.env` con `NOMBRE_BUCKET` (copiado de `.env.example`). Ejecutar desde la raíz del repositorio con Bash (Linux, macOS o Git Bash en Windows):

```bash
bash infra/verificar_entorno.sh     # AWS CLI v2, identidad, región, LabRole, LabInstanceProfile, roles EMR
bash infra/crear_datalake.sh        # crea el bucket (si no existe), bloquea acceso público y crea prefijos .keep
bash infra/destruir_datalake.sh     # vacía y borra el bucket tras escribir su nombre para confirmar
```

`crear_datalake.sh` es idempotente: puede ejecutarse varias veces.

## Evidencias

<!-- Capturas en docs/evidencias/ y enlaces aquí. -->
