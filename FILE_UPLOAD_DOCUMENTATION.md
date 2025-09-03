# HAVAS Agent HR - File Upload Feature

## Nuevas funcionalidades implementadas

### 1. Subida de Archivos
- **Tipos soportados**: PDF y XLSX únicamente
- **Tamaño máximo**: 10MB por archivo
- **Método de subida**: 
  - Clic en el botón "Upload File" del menú desplegable
  - Arrastrar y soltar archivos en el área de chat

### 2. Procesamiento de Archivos
- **PDF**: Extracción de texto de todas las páginas
- **XLSX**: Extracción de datos de todas las hojas del libro
- **Validación**: Solo se aceptan archivos con extensiones .pdf y .xlsx

### 3. Priorización de Contenido
- **Archivos subidos**: Cuando hay archivos cargados, el agente utiliza ÚNICAMENTE el contenido de estos archivos
- **Azure AI Search**: Solo se utiliza cuando NO hay archivos subidos en la sesión
- **Indicador visual**: Se muestra la fuente del contexto usado (archivos subidos vs base de conocimiento)

### 4. Gestión de Sesiones y Limpieza Automática ✨ NUEVO ✨
- **Sesión única**: Cada conversación tiene un ID de sesión único
- **Archivos por sesión**: Los archivos solo están disponibles en su sesión específica
- **Limpieza automática**:
  - **Al cerrar la página**: Los archivos se eliminan automáticamente cuando el usuario cierra la pestaña
  - **Al refrescar**: Los archivos se limpian si se recarga la página
  - **Nueva conversación**: Al hacer clic en "New chat", se eliminan todos los archivos de la sesión anterior
  - **Limpieza periódica**: El servidor elimina automáticamente archivos antiguos (>2 horas) cada 30 minutos
  - **Limpieza manual**: Endpoint disponible para limpiar archivos específicos de una sesión

### 5. Interfaz de Usuario
- **Botón de subida**: Nuevo botón en el menú desplegable
- **Área de archivos**: Se muestra una lista de archivos subidos con información básica
- **Notificaciones**: Confirmaciones visuales para subidas exitosas y errores
- **Drag & Drop**: Funcionalidad completa de arrastrar y soltar

## Endpoints API

### POST /api/upload
Sube un archivo a la sesión especificada.

**Parámetros:**
- `file`: Archivo (PDF o XLSX)
- `sessionId`: ID de la sesión

### GET /api/files/{session_id}
Obtiene la lista de archivos subidos para una sesión.

### DELETE /api/files/{session_id} ✨ NUEVO ✨
Elimina todos los archivos de una sesión específica.

**Respuesta:**
```json
{
  "success": true,
  "message": "Files cleared for session session_123",
  "timestamp": "2025-09-02T..."
}
```

### POST /api/cleanup ✨ NUEVO ✨
Ejecuta limpieza manual de archivos antiguos.

**Respuesta:**
```json
{
  "success": true,
  "deleted_files": 5,
  "message": "Cleaned up 5 old files",
  "timestamp": "2025-09-02T..."
}
```

## Estrategias de Limpieza Implementadas

### 1. **Limpieza al Cerrar Página**
- Utiliza `navigator.sendBeacon()` para envío confiable
- Eventos: `beforeunload`, `pagehide`, `visibilitychange`
- Funciona incluso si el usuario cierra bruscamente la pestaña

### 2. **Limpieza en Nueva Conversación**
- Se ejecuta automáticamente al hacer clic en "New chat"
- Limpia archivos del servidor antes de generar nueva sesión

### 3. **Limpieza Periódica Automática**
- Hilo en segundo plano que se ejecuta cada 30 minutos
- Elimina archivos con más de 2 horas de antigüedad
- No afecta el rendimiento de la aplicación

### 4. **Limpieza Manual**
- Endpoint `/api/cleanup` para administradores
- Permite ajustar el tiempo de antigüedad para limpieza

## Archivos Modificados

### Backend
- `app.py`: Nuevos endpoints DELETE y cleanup, hilo de limpieza periódica
- `agents/tv_agent.py`: Método para limpiar archivos de sesión
- `tools/file_processor.py`: Método para limpieza automática por tiempo
- `requirements.txt`: Sin cambios adicionales

### Frontend
- `public/index.html`: Sin cambios en estructura
- `public/css/styles.css`: Sin cambios adicionales
- `public/js/chat.js`: Lógica de limpieza automática y eventos de página
- `public/test.html`: Funcionalidad de limpieza agregada

## Flujo de Limpieza

1. **Usuario sube archivos** → Archivos guardados con timestamp
2. **Usuario usa archivos normalmente** → Sin limpieza
3. **Cualquier evento de cierre**:
   - Página cerrada → Limpieza inmediata vía sendBeacon
   - Nueva conversación → Limpieza vía DELETE API
   - Tiempo transcurrido (2h) → Limpieza automática en segundo plano

## Configuración de Limpieza

```javascript
// Configuración en JavaScript (modificable)
const CLEANUP_EVENTS = ['beforeunload', 'pagehide', 'visibilitychange'];
const CLEANUP_DELAY = 100; // ms

// Configuración en Python (modificable)
PERIODIC_CLEANUP_INTERVAL = 1800  # 30 minutos
MAX_FILE_AGE_HOURS = 2            # 2 horas
```

## Beneficios de la Limpieza Automática

✅ **Sin acumulación**: Los archivos no se acumulan en el servidor  
✅ **Privacidad**: Los archivos se eliminan automáticamente  
✅ **Rendimiento**: El servidor no se satura con archivos antiguos  
✅ **Espacio en disco**: Uso eficiente del almacenamiento  
✅ **Fiabilidad**: Múltiples estrategias garantizan la limpieza  

## Limitaciones

- Los archivos pueden persistir brevemente si la conexión se pierde durante el cierre
- La limpieza periódica mínima es cada 30 minutos
- Solo se aplica a archivos PDF y XLSX en la carpeta `uploads/`

## Uso Recomendado

1. **Uso normal**: Los archivos se limpian automáticamente, no requiere acción del usuario
2. **Para administradores**: Usar `/api/cleanup` si se necesita limpieza inmediata
3. **Desarrollo**: Los archivos de prueba se eliminan automáticamente
