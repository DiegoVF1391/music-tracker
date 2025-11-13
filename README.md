# 🎵 Music Tracker  

**Music Tracker** es una aplicación web creada para gestionar y monitorear canciones dentro de un sistema de control interno.  
Permite visualizar métricas, fechas de vencimiento y reportes con una interfaz moderna construida sobre **Flask**, **Bootstrap** y **PostgreSQL (Supabase)**.  

🌐 **Demo:** [https://music-tracker-pqwv.onrender.com](https://music-tracker-pqwv.onrender.com)

---

## 🚀 Tecnologías principales

| Categoría | Herramientas |
|------------|---------------|
| Backend | 🐍 Flask |
| Base de datos | 🐘 PostgreSQL (Supabase) |
| Frontend | 💅 HTML, CSS, Bootstrap |
| Interactividad | ⚡ JavaScript |
| Hosting | ☁️ Render |

---

## ✨ Características principales

- 📊 **Dashboard interactivo:** visualiza métricas, gráficas y alertas en tiempo real.  
- 🎧 **Gestión de canciones:** listado dinámico de canciones y fechas próximas a vencer.  
- 🧮 **Reportes automáticos:** tablas dinámicas y gráficas generadas desde datos reales.  
- 📱 **Diseño responsivo:** totalmente adaptable a móviles, tablets y escritorio.  
- 🌙 **Modo oscuro:** interfaz optimizada para fondos oscuros (`#0f0f0f`).  

---

## 🛠️ Instalación y configuración local

```bash
# 1️⃣ Clonar el repositorio
git clone https://github.com/tu-usuario/music-tracker.git

# 2️⃣ Entrar al directorio
cd music-tracker

# 3️⃣ Crear entorno virtual
python -m venv venv
source venv/bin/activate  # (en mac/linux)
venv\Scripts\activate     # (en windows)

# 4️⃣ Instalar dependencias
pip install -r requirements.txt

# 5️⃣ Configurar variables de entorno
# (Ejemplo en .env.example)
FLASK_APP=app.py  
SUPABASE_URL=tu_url  
SUPABASE_KEY=tu_api_key  

# 6️⃣ Ejecutar el servidor
flask run
