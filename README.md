# 🏛️ ArchEstate - The Private Ledger

## 📖 Sobre el Proyecto
ArchEstate es una plataforma privada diseñada para conectar clientes de alto nivel adquisitivo (que buscan comprar, construir o remodelar propiedades) con profesionales verificados del sector inmobiliario y arquitectónico. 

Este MVP (Producto Mínimo Viable) se centra en la captura limpia de oportunidades de negocio (leads), protegiendo la privacidad de los clientes mediante un sistema de revelación de datos bajo demanda y trazabilidad absoluta.

## ✨ Características del MVP
* **Portal de Clientes:** Formulario minimalista de alta conversión para la captura de requerimientos.
* **Dashboard de Profesionales:** Panel seguro con protección de datos (los teléfonos de los clientes se revelan individualmente mediante consultas a la API).
* **Panel de Administración:** Directorio de profesionales y registro de auditoría en tiempo real.
* **Seguridad:** Autenticación por sesiones y protección de rutas.

## 🛠️ Stack Tecnológico
* **Backend:** Python 3, Flask.
* **Base de Datos:** SQLite (con autogeneración de esquema).
* **Frontend:** HTML5, Tailwind CSS (CDN), Vanilla JavaScript.
* **Diseño UI:** Figma / Lucide Icons.

---

## 🚀 Guía de Instalación para el Equipo

Sigue estos pasos para levantar el entorno de desarrollo local:

### 1. Clonar el repositorio
```bash
git clone [https://github.com/TU-USUARIO/archestate.git](https://github.com/TU-USUARIO/archestate.git)
cd archestate

# Crear entorno
python -m venv venv

# Activar en Windows:
venv\Scripts\activate

# Activar en Mac/Linux:
source venv/bin/activate

# Instalar las dependencias:
pip install -r requirements.txt

# Iniciar en el servidor:
python app.py
