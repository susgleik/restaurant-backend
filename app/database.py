from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.config import settings
import asyncio
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variable para el cliente de MongoDB
mongodb_client: AsyncIOMotorClient = None
database = None

async def connect_to_mongo():
    """Conectar a MongoDB"""
    global mongodb_client, database
    
    try:
        # Configuración más simple y limpia para Motor/PyMongo
        mongodb_client = AsyncIOMotorClient(
            settings.mongodb_url,
            # Opciones básicas y compatibles
            maxPoolSize=50,
            minPoolSize=10,
            maxIdleTimeMS=30000,  # Usar maxIdleTimeMS en lugar de maxConnectionIdleTime
            serverSelectionTimeoutMS=5000,
            socketTimeoutMS=20000,
            connectTimeoutMS=10000,
            heartbeatFrequencyMS=10000,
            retryWrites=True,
            w="majority"
        )
        
        # Verificar la conexión
        await mongodb_client.admin.command('ping')
        logger.info("✅ Connected to MongoDB successfully")
        
        # Obtener la base de datos
        database = mongodb_client[settings.database_name]
        logger.info(f"✅ Database '{settings.database_name}' selected")
        
        return mongodb_client
        
    except Exception as e:
        logger.error(f"❌ Error connecting to MongoDB: {e}")
        raise e

async def init_db():
    """Inicializar la base de datos y Beanie"""
    global database
    
    try:
        # Conectar a MongoDB
        client = await connect_to_mongo()
        
        # Importar todos los modelos
        from app.models.user import User
        from app.models.category import Category
        from app.models.menu_item import MenuItem
        from app.models.order import Order
        from app.models.cart_item import CartItem
        
        # Inicializar Beanie con todos los modelos
        await init_beanie(
            database=database,
            document_models=[
                User,
                Category,
                MenuItem,
                Order,
                CartItem
            ]
        )
        
        logger.info("✅ Database initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Error initializing database: {e}")
        raise e

async def close_mongo_connection():
    """Cerrar la conexión a MongoDB"""
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()
        logger.info("✅ MongoDB connection closed")

def get_database():
    """Obtener la instancia de la base de datos"""
    return database