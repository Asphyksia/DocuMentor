================================================================================
                    DOCUMENTOR - PRIORIDADES DE MEJORA
                    Ordenado de MÁS a MENOS importante
================================================================================
Generado: 26 de marzo de 2026
Basado en: Auditoría completa del código


================================================================================
PRIORIDAD 1: CRÍTICO (Sin esto, no puedes ponerse en producción)
================================================================================

1. [BACKEND] SISTEMA DE AUTENTICACIÓN
   ─────────────────────────────────────
   Por qué: Cualquiera que acceda a localhost:8001 puede subir/borrar documentos
   y hacer consultas. Sin auth, es una demo, no un producto.
   
   Qué hacer:
   - Añade login básico con usuario/contraseña en .env
   - Genera un token JWT al hacer login
   - El frontend guarda el token en localStorage
   - El bridge valida el token en cada conexión WebSocket
   - Añade un campo user_id a cada space y documento
   
   Dificultad: Media
   Tiempo estimado: 1-2 días
   
   Archivos a tocar:
   - backend/bridge.py (añadir validación de token)
   - backend/mcp_wrapper.py (filtrar por user_id)
   - frontend/hooks/useBridge.ts (enviar token)
   - frontend/components/LoginForm.tsx (NUEVO)

---

2. [BACKEND] CERRAR CORS
   ─────────────────────────────────────
   Por qué: allow_origins=["*"] permite que CUALQUIER web haga peticiones
   a tu backend. Abre la puerta a ataques CSRF.
   
   Qué hacer:
   - En bridge.py, línea 183, cambia:
     
     ANTES:
     allow_origins=["*"]
     
     DESPUÉS:
     allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"]
   
   - Añade variable de entorno ALLOWED_ORIGINS para producción
   
   Dificultad: Fácil
   Tiempo estimado: 10 minutos

---

3. [BACKEND] RATE LIMITING BÁSICO
   ─────────────────────────────────────
   Por qué: Sin límite, alguien puede tumbar tu servidor con peticiones
   o saturar tu cuenta de API de LLM.
   
   Qué hacer:
   - Añade un contador de peticiones por IP/conexión
   - Límite simple: 20 peticiones por minuto por WebSocket
   - Si excede, envía error y cierra conexión temporalmente
   
   Código ejemplo para bridge.py:
   
   from collections import defaultdict
   from datetime import datetime, timedelta
   
   _rate_limits = defaultdict(list)
   
   def check_rate_limit(ws_id: int, max_requests: int = 20) -> bool:
       now = datetime.now()
       requests = _rate_limits[ws_id]
       requests = [t for t in requests if now - t < timedelta(minutes=1)]
       _rate_limits[ws_id] = requests
       if len(requests) >= max_requests:
           return False
       requests.append(now)
       return True
   
   Dificultad: Fácil-Media
   Tiempo estimado: 2-3 horas


================================================================================
PRIORIDAD 2: IMPORTANTE (Mejora significativamente la experiencia)
================================================================================

4. [FRONTEND] INDICADORES DE CARGA Y ESTADOS VACÍOS
   ─────────────────────────────────────
   Por qué: Cuando algo tarda o falla, el usuario no sabe qué pasa.
   La sidebar de documentos aparece vacía mientras carga sin explicación.
   
   Qué hacer:
   - Añade esqueletos de carga (skeleton loaders) en DocSidebar
   - Muestra mensaje cuando no hay documentos: "Sube tu primer documento"
   - Añade indicador visual cuando el WebSocket se reconecta
   - Muestra progreso real durante upload (no solo "Subiendo...")
   
   Archivos a tocar:
   - frontend/components/DocSidebar.tsx
   - frontend/hooks/useDocumentsState.ts
   - frontend/components/UploadModal.tsx
   
   Dificultad: Fácil
   Tiempo estimado: 3-4 horas

---

5. [FRONTEND] MANEJO DE ERRORES EN UI
   ─────────────────────────────────────
   Por qué: Ahora los errores aparecen como texto rojo en el chat.
   No hay forma de reintentar. El usuario queda bloqueado.
   
   Qué hacer:
   - Añade botón "Reintentar" cuando falla una query
   - Muestra errores de conexión con instrucciones claras
   - Añade un toast notification para errores no relacionados con chat
   - Guarda mensajes fallidos para poder reenviarlos
   
   Archivos a tocar:
   - frontend/components/ChatPanel.tsx
   - frontend/hooks/useChatState.ts
   - frontend/components/ui/toast.tsx (NUEVO - shadcn tiene uno)
   
   Dificultad: Media
   Tiempo estimado: 4-5 horas

---

6. [BACKEND] ELIMINAR QUERY LOCK (Concurrencia)
   ─────────────────────────────────────
   Por qué: Ahora mismo solo UNA persona puede hacer consultas a la vez.
   Si dos usuarios consultan, uno espera al otro. No escala.
   
   Qué hacer (opción simple):
   - Crea un AIAgent por cada conexión WebSocket, no singleton
   - O usa un pool de agentes (más complejo)
   
   Código ejemplo:
   
   ANTES (bridge.py línea 227):
   _agent_instance: "AIAgent | None" = None
   
   DESPUÉS:
   _agent_pool: dict[int, "AIAgent"] = {}  # Una por ws_id
   
   Y en websocket_endpoint, crear/agente para esa conexión:
   
   if ws_id not in _agent_pool:
       _agent_pool[ws_id] = _create_agent()
   
   Dificultad: Media
   Tiempo estimado: 2-3 horas

---

7. [BACKEND] LOGS ESTRUCTURADOS
   ─────────────────────────────────────
   Por qué: Cuando algo falla en producción, necesitas saber QUÉ pasó.
   Ahora mismo los logs son texto plano difícil de buscar.
   
   Qué hacer:
   - Usa structlog o loguru en lugar de logging básico
   - Cada petición tiene un ID único para rastrear
   - Logs en JSON para poder enviarlos a herramientas de monitoreo
   
   Ejemplo:
   
   import structlog
   
   logger = structlog.get_logger()
   logger.info("query_received", query=query[:50], user_id=user_id, ws_id=ws_id)
   
   Dificultad: Fácil
   Tiempo estimado: 2 horas


================================================================================
PRIORIDAD 3: MEJORAS DE UX (Hacen el producto más pulido)
================================================================================

8. [FRONTEND] SIDEBAR DE DOCUMENTOS MÁS FUNCIONAL
   ─────────────────────────────────────
   Por qué: Ahora solo muestra nombre y tipo. No hay búsqueda,
   no hay filtros, no hay vista previa.
   
   Qué hacer:
   - Añade buscador de documentos en la sidebar
   - Muestra fecha de subida y tamaño
   - Añade botón de "más opciones" (renombrar, descargar, info)
   - Muestra miniatura o icono según tipo de documento
   - Añade confirmación antes de borrar
   
   Archivos a tocar:
   - frontend/components/DocSidebar.tsx
   - frontend/components/ui/alert-dialog.tsx (para confirmar borrado)
   
   Dificultad: Media
   Tiempo estimado: 1 día

---

9. [FRONTEND] HISTORIAL DE CONVERSACIONES
   ─────────────────────────────────────
   Por qué: Ahora si recargas la página, pierdes todo el chat.
   No hay forma de ver conversaciones anteriores.
   
   Qué hacer:
   - Guarda el historial en localStorage como mínimo
   - Mejor: guarda en el backend asociado a cada thread de SurfSense
   - Añade una lista de "conversaciones anteriores" en la UI
   - Permite renombrar conversaciones
   
   Archivos a tocar:
   - frontend/hooks/useChatState.ts
   - frontend/components/ChatPanel.tsx
   - backend/bridge.py (nuevo handler: list_threads, get_thread_history)
   
   Dificultad: Media
   Tiempo estimado: 1 día

---

10. [FRONTEND] RESPONSIVE DESIGN PARA MÓVIL
    ─────────────────────────────────────
    Por qué: La interfaz no está optimizada para pantallas pequeñas.
    La sidebar se come el espacio, los gráficos se ven mal.
    
    Qué hacer:
    - Sidebar colapsable en móvil (drawer desde la izquierda)
    - Chat ocupa todo el ancho en móvil
    - Dashboard con scroll horizontal o gráficos apilados
    - Botón de "nuevo chat" accesible desde cualquier lugar
    
    Archivos a tocar:
    - frontend/app/page.tsx
    - frontend/components/DocSidebar.tsx
    - frontend/DashboardRenderer.tsx
    
    Dificultad: Media
    Tiempo estimado: 1 día

---

11. [FRONTEND] ATAJOS DE TECLADO
    ─────────────────────────────────────
    Por qué: Los usuarios avanzados quieren ir rápido.
    Poder hacer todo sin tocar el ratón es un plus.
    
    Qué hacer:
    - Ctrl+Enter para enviar mensaje
    - Ctrl+U para abrir modal de upload
    - Ctrl+N para nuevo chat
    - Ctrl+/ para mostrar atajos disponibles
    - Escape para cerrar modales
    
    Archivos a tocar:
    - frontend/app/page.tsx
    - frontend/components/ChatPanel.tsx
    - frontend/components/UploadModal.tsx
    
    Dificultad: Fácil
    Tiempo estimado: 2-3 horas


================================================================================
PRIORIDAD 4: NICE TO HAVE (Mejoras de calidad, no urgentes)
================================================================================

12. [BACKEND] TESTS BÁSICOS
    ─────────────────────────────────────
    Por qué: Sin tests, cada cambio puede romper algo sin que te des cuenta.
    
    Qué hacer:
    - Tests de los handlers del bridge (puedes usar fixtures simples)
    - Tests de validación de Pydantic models
    - Un test de integración: subir documento → hacer query → obtener respuesta
    
    Dificultad: Media-Alta (si no has hecho tests antes)
    Tiempo estimado: 2-3 días

---

13. [BACKEND] CONFIGURACIÓN DE MODELO EN UI
    ─────────────────────────────────────
    Por qué: Para cambiar de modelo hay que editar .env y reiniciar.
    Debería poderse hacer desde la interfaz.
    
    Qué hacer:
    - Añade endpoint GET /models que liste modelos disponibles
    - Añade endpoint POST /settings para cambiar modelo
    - Settings panel en el frontend con selector de modelo
    - Muestra costo estimado por consulta (aproximado)
    
    Dificultad: Media
    Tiempo estimado: 1 día

---

14. [FRONTEND] TEMA CLARO/OSCURO
    ─────────────────────────────────────
    Por qué: Ahora solo hay tema oscuro. Algunos usuarios prefieren claro.
    
    Qué hacer:
    - Usa next-themes para gestionar el tema
    - Añade toggle en el header
    - Ajusta colores de gráficos para ambos temas
    
    Dificultad: Fácil
    Tiempo estimado: 3-4 horas

---

15. [FRONTEND] EXPORTAR RESULTADOS
    ─────────────────────────────────────
    Por qué: Un usuario puede querer guardar el dashboard o la respuesta
    como PDF o imagen para compartir.
    
    Qué hacer:
    - Botón "Exportar como imagen" en el dashboard
    - Botón "Copiar respuesta" en cada mensaje del chat
    - Opción de "Exportar conversación completa"
    
    Dificultad: Media
    Tiempo estimado: 1 día


================================================================================
PRIORIDAD 5: FUTURO (Para cuando tengas tiempo)
================================================================================

16. Multi-tenancy real (cada usuario ve solo sus documentos)
17. Compartir documentos/espacios entre usuarios
18. Webhooks para integraciones
19. API REST pública documentada con Swagger
20. Plugin para navegadores (subir PDFs desde cualquier web)
21. App móvil (React Native)
22. Cola de procesamiento de documentos con progreso en tiempo real


================================================================================
RESUMEN - TOP 5 PARA EMPEZAR
================================================================================

Si solo tienes un día, haz ESTO:

1. ⏱️  10 min  → Cerrar CORS (línea 183 de bridge.py)
2. ⏱️  2 horas → Rate limiting básico
3. ⏱️  3 horas → Mejorar estados de carga en frontend
4. ⏱️  3 horas → Manejo de errores con botón "Reintentar"
5. ⏱️  1 día   → Sistema de autenticación básico

Con esto, el proyecto pasa de "demo" a "MVP usable por otras personas".


================================================================================
NOTAS FINALES
================================================================================

- El orden está basado en qué permite que OTROS usen tu proyecto
- Autenticación es lo que separa "proyecto personal" de "producto"
- El frontend tiene buena base, le falta pulido, no reescritura
- No intentes hacer todo a la vez. Prioriza. Un feature a la vez.

================================================================================
