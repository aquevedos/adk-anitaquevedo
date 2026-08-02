# Guía de Instalación de `jq`

Este documento describe cómo instalar **`jq`** en diferentes entornos y sistemas operativos, incluyendo la instalación en Linux sin necesidad de permisos de superusuario (`root`/`sudo`).

---

## 1. Instalación en Linux sin permisos de Root (Recomendada para entornos restringidos / Cloud Shell)

Si no cuentas con permisos de `sudo` o `root` (lo que causaría un error con `apt install jq`), puedes instalar el binario oficial precompilado directamente en el directorio de binarios de tu usuario (`~/.local/bin/`):

```bash
# Crear directorio local si no existe, descargar binario, otorgar permisos de ejecución y verificar
mkdir -p ~/.local/bin
curl -sSL -o ~/.local/bin/jq https://github.com/jqlang/jq/releases/download/jq-1.7.1/jq-linux-amd64
chmod +x ~/.local/bin/jq
jq --version
```

### Comprobación del `$PATH`

Asegúrate de que `~/.local/bin` esté incluido en tu variable `$PATH`:

```bash
which jq
# Salida esperada: /home/<usuario>/.local/bin/jq (o similar)
```

Si el comando no es detectado, añade la ruta a tu archivo `~/.bashrc`:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

---

## 2. Instalación en Linux con permisos de Administrador (`sudo`)

### Debian / Ubuntu / Linux Mint
```bash
sudo apt-get update && sudo apt-get install -y jq
```

### RHEL / CentOS / Fedora / Rocky Linux
```bash
# Fedora / RHEL 8+
sudo dnf install -y jq

# CentOS 7
sudo yum install -y epel-release && sudo yum install -y jq
```

### Arch Linux
```bash
sudo pacman -S jq
```

---

## 3. Instalación en macOS

### Mediante Homebrew
```bash
brew install jq
```

### Mediante MacPorts
```bash
sudo port install jq
```

---

## 4. Instalación mediante gestores de paquetes de Python / Conda

Si utilizas entornos virtuales de Python o Conda:

```bash
# Mediante Conda / Mamba
conda install -c conda-forge jq
```
