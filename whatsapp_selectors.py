"""
WhatsApp Selectors - Selectores CSS y XPath para WhatsApp Web 2025.
Mantiene un único punto de cambio cuando WhatsApp actualiza su UI.
"""

# ============================================================================
# CONEXIÓN Y AUTENTICACIÓN
# ============================================================================
URL_WHATSAPP = "https://web.whatsapp.com"

# Sidebar - busca por data-testid que es más estable
SELECTOR_SIDEBAR = '//div[@data-testid="chat-list"]'

# QR Code - busca canvas con imagen del QR
SELECTOR_QR_CODE = '//canvas[contains(@class, "qr")]'

# ============================================================================
# SELECCIÓN DE CHATS
# ============================================================================
# Buscador - nuevo selector para WhatsApp actual
SELECTOR_SEARCH_BOX = 'div[data-testid="chat-list-search"] input'

# Lista de chats
SELECTOR_SIDEBAR_CHAT_LIST = 'div[data-testid="chat-list"]'
SELECTOR_CHAT_ITEM = '//div[@data-testid="chat-list"]//div[@aria-label]'
SELECTOR_CHAT_TITLE = './/span[@title]'
SELECTOR_CHAT_HEADER = '//header//span[@title]'
SELECTOR_CONVERSATION_PANEL = '//div[@data-testid="conversation-panel-messages"]'
SELECTOR_ICON_GROUP = '//span[@data-testid="group"]'
SELECTOR_ICON_GROUP_CHAT = '//div[@data-testid="chat-info"]'

# ============================================================================
# MENSAJES
# ============================================================================
SELECTOR_MSG_CONTAINER = 'div[data-testid="msg-container"]'
SELECTOR_MSG_TEXT = (
    'div[data-testid="msg-text"] span'
)
SELECTOR_MSG_META = '//span[@data-testid="msg-time"]'
SELECTOR_MSG_OUTGOING = 'div[data-testid="outgoing"]'
SELECTOR_MSG_INCOMING = 'div[data-testid="incoming"]'
SELECTOR_MESSAGE_LIST = 'div[data-testid="message-list"]'

# ============================================================================
# ENVÍO DE MENSAJES
# ============================================================================
SELECTOR_COMPOSE_BOX = 'div[data-testid="conversation-compose-box-input"]'
SELECTOR_COMPOSE_BOX_ALT = 'div[title="Escribe un mensaje"]'
SELECTOR_COMPOSE_INPUT = (
    'div[data-testid="conversation-compose-box-input"] '
    'div[contenteditable="true"][data-tab="10"]'
)
SELECTOR_SEND_BUTTON = 'button[data-testid="send"]'
SELECTOR_SEND_BUTTON_ALT = 'span[data-testid="send"]'

# ============================================================================
# CONFIGURACIÓN DE NAVEGADOR
# ============================================================================
CHROME_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--window-size=1280,800",
    "--disable-blink-features=AutomationControlled",
]