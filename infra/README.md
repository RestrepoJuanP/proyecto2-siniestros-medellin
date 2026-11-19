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

### Ciclo de vida de las fuentes (Punto 2)

Las fuentes se crean desde [punto2_fuentes/](../punto2_fuentes/README.md) (por ejemplo `punto2_fuentes/rds/crear_rds.sh`). Estos scripts las administran entre sesiones:

```bash
bash infra/pausar_fuentes.sh       # detiene la RDS y la EC2 de fuentes (si ID_INSTANCIA_EC2_FUENTES está en .env)
bash infra/reanudar_fuentes.sh     # las inicia y espera a que estén disponibles
bash infra/destruir_fuentes.sh     # borra la RDS (sin snapshot), termina la EC2 y borra ambos security groups; pide escribir DESTRUIR
```

- AWS vuelve a iniciar automáticamente una RDS detenida después de 7 días.
- Después de `reanudar_fuentes.sh`, si cambió de red, ejecute `bash punto2_fuentes/rds/actualizar_mi_ip.sh`.
- [funciones_comunes.sh](funciones_comunes.sh) no se ejecuta solo. Agrupa funciones compartidas: leer y escribir `.env` sin duplicar claves, detectar la IP pública, buscar security groups y consultar estados.

## Evidencias

<!-- Capturas en docs/evidencias/ y enlaces aquí. -->
