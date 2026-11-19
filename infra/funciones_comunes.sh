#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# funciones_comunes.sh
# Funciones compartidas por los scripts bash del proyecto. NO se ejecuta solo:
# se carga con   source "${DIR_RAIZ}/infra/funciones_comunes.sh"
# El script que lo carga debe definir antes DIR_RAIZ (raíz del repositorio).
#
# Nota: las funciones que "retornan" un valor lo hacen con echo por stdout;
# por eso todos los mensajes informativos van a stderr (>&2).
# -----------------------------------------------------------------------------

REGION="us-east-1"
ARCHIVO_ENV="${DIR_RAIZ}/.env"

# Mensajes estandarizados (a stderr para no contaminar valores capturados)
mensaje_info()  { echo "[INFO]  $*" >&2; }
mensaje_ok()    { echo "[OK]    $*" >&2; }
mensaje_aviso() { echo "[AVISO] $*" >&2; }
mensaje_error() { echo "[ERROR] $*" >&2; }

# Quita retornos de carro (\r) que agrega la AWS CLI en Windows / Git Bash
# y convierte tabulaciones (separador de --output text) en espacios.
limpiar_salida() {
    tr -d '\r' | tr '\t' ' '
}

# Lee una variable del archivo .env sin ejecutarlo. Retorna vacío si no existe.
leer_variable_env() {
    local nombre_variable="$1"
    local valor=""
    if [[ -f "${ARCHIVO_ENV}" ]]; then
        valor="$(grep -E "^${nombre_variable}=" "${ARCHIVO_ENV}" | tail -n 1 | cut -d '=' -f 2- | tr -d '\r"' || true)"
    fi
    echo "${valor}"
}

# Lee una variable del .env; si está vacía retorna el valor por defecto indicado.
leer_variable_env_o_defecto() {
    local nombre_variable="$1"
    local valor_por_defecto="$2"
    local valor
    valor="$(leer_variable_env "${nombre_variable}")"
    if [[ -z "${valor}" ]]; then
        valor="${valor_por_defecto}"
    fi
    echo "${valor}"
}

# Crea o actualiza una clave en .env sin duplicarla (conserva el resto del archivo).
escribir_variable_env() {
    local nombre_variable="$1"
    local valor="$2"
    local archivo_temporal="${ARCHIVO_ENV}.tmp"

    if [[ ! -f "${ARCHIVO_ENV}" ]]; then
        touch "${ARCHIVO_ENV}"
    fi

    if grep -qE "^${nombre_variable}=" "${ARCHIVO_ENV}"; then
        # Reemplaza todas las apariciones de la clave por una sola línea nueva
        awk -v clave="${nombre_variable}" -v nuevo_valor="${valor}" '
            BEGIN { ya_escrita = 0 }
            {
                linea = $0
                sub(/\r$/, "", linea)
                if (index(linea, clave "=") == 1) {
                    if (ya_escrita == 0) {
                        print clave "=" nuevo_valor
                        ya_escrita = 1
                    }
                } else {
                    print linea
                }
            }
        ' "${ARCHIVO_ENV}" > "${archivo_temporal}"
        mv "${archivo_temporal}" "${ARCHIVO_ENV}"
    else
        # Asegura salto de línea final antes de agregar la clave
        if [[ -s "${ARCHIVO_ENV}" && -n "$(tail -c 1 "${ARCHIVO_ENV}")" ]]; then
            echo "" >> "${ARCHIVO_ENV}"
        fi
        echo "${nombre_variable}=${valor}" >> "${ARCHIVO_ENV}"
    fi
}

# Verifica que la AWS CLI exista y que las credenciales del Learner Lab sean válidas.
verificar_aws_cli() {
    if ! command -v aws >/dev/null 2>&1; then
        mensaje_error "No se encontró la AWS CLI. Ejecute primero: bash infra/verificar_entorno.sh"
        exit 1
    fi
    if ! aws sts get-caller-identity --region "${REGION}" >/dev/null 2>&1; then
        mensaje_error "Credenciales AWS inválidas o vencidas. Actualice ~/.aws/credentials desde 'AWS Details' del Learner Lab."
        exit 1
    fi
}

# Detecta la IP pública actual del equipo.
obtener_ip_publica() {
    local ip
    ip="$(curl -s --max-time 15 https://checkip.amazonaws.com | tr -d '\r\n ')"
    if [[ ! "${ip}" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        mensaje_error "No fue posible detectar la IP pública (respuesta: '${ip}')."
        exit 1
    fi
    echo "${ip}"
}

# Retorna el ID del VPC por defecto de la región.
obtener_vpc_por_defecto() {
    local id_vpc
    id_vpc="$(aws ec2 describe-vpcs \
        --region "${REGION}" \
        --filters Name=is-default,Values=true \
        --query 'Vpcs[0].VpcId' \
        --output text | limpiar_salida)"
    if [[ -z "${id_vpc}" || "${id_vpc}" == "None" ]]; then
        mensaje_error "No existe un VPC por defecto en ${REGION}."
        exit 1
    fi
    echo "${id_vpc}"
}

# Retorna el ID de un security group por nombre dentro del VPC indicado (vacío si no existe).
buscar_security_group() {
    local nombre_grupo="$1"
    local id_vpc="$2"
    local id_grupo
    id_grupo="$(aws ec2 describe-security-groups \
        --region "${REGION}" \
        --filters "Name=group-name,Values=${nombre_grupo}" "Name=vpc-id,Values=${id_vpc}" \
        --query 'SecurityGroups[0].GroupId' \
        --output text | limpiar_salida)"
    if [[ "${id_grupo}" == "None" ]]; then
        id_grupo=""
    fi
    echo "${id_grupo}"
}

# Retorna el estado de una instancia RDS, o "no-existe".
obtener_estado_rds() {
    local identificador="$1"
    local estado
    if estado="$(aws rds describe-db-instances \
        --region "${REGION}" \
        --db-instance-identifier "${identificador}" \
        --query 'DBInstances[0].DBInstanceStatus' \
        --output text 2>/dev/null | limpiar_salida)"; then
        echo "${estado}"
    else
        echo "no-existe"
    fi
}

# Retorna el estado de una instancia EC2, o "no-existe".
obtener_estado_ec2() {
    local id_instancia="$1"
    local estado
    if estado="$(aws ec2 describe-instances \
        --region "${REGION}" \
        --instance-ids "${id_instancia}" \
        --query 'Reservations[0].Instances[0].State.Name' \
        --output text 2>/dev/null | limpiar_salida)"; then
        echo "${estado}"
    else
        echo "no-existe"
    fi
}
