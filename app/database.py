from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import asyncio
from typing import Optional

from app.config import settings

# Variable global para el cliente de MongoDB
mongodb_client: Optional[AsyncIOMotorClient] = None

async def connect_to_mongo():
    """Conectar a MongoDB Atlas"""
    global mongodb_client
    try:
        # Crear cliente de MongoDB
        mongodb_client = AsyncIOMotorClient(
            settings.mongodb_url,
            maxPoolSize=10,
            minPoolSize=10,
            maxIdleTimeMS=45000,
            maxConnectionIdleTime=10000,
            heartbeatFrequencyMS=10000,
            connectTimeoutMS=20000,
            serverSelectionTimeoutMS=20000,
        )
        
        # Verificar la conexión
        await mongodb_client.admin.command('ping')
        print("✅ Successfully connected to MongoDB Atlas!")
        
        return mongodb_client
        
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        raise e

async def close_mongo_connection():
    """Cerrar conexión a MongoDB"""
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()
        print("🔌 Disconnected from MongoDB")

async def init_db():
    """Inicializar la base de datos y los modelos de Beanie"""
    try:
        # Conectar a MongoDB
        client = await connect_to_mongo()
        print(client, 'se ejucto')
        
        # Importar todos los modelos
        from app.models.user import User
        from app.models.category import Category
        from app.models.menu_item import MenuItem
        from app.models.order import Order
        from app.models.cart_item import CartItem
        
        # Obtener la base de datos
        database = client[settings.database_name]
        
        # Inicializar Beanie con todos los modelos
        await init_beanie(
            database=database,
            document_models=[
                User,
                Category,
                MenuItem,
                Order,
                CartItem,
            ],
        )
        
        print("🚀 Database and Beanie initialized successfully!")
        
        # Crear índices adicionales si es necesario
        await create_indexes()
        
        # Crear datos iniciales si no existen
        await create_initial_data()
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        raise e

async def create_indexes():
    """Crear índices adicionales para mejorar el rendimiento"""
    try:
        from app.models.user import User
        from app.models.menu_item import MenuItem
        from app.models.order import Order
        from app.models.cart_item import CartItem
        
        # Índices para usuarios
        await User.create_index("email", unique=True)
        await User.create_index("username", unique=True)
        
        # Índices para menu items
        await MenuItem.create_index("category_id")
        await MenuItem.create_index("available")
        await MenuItem.create_index([("name", "text"), ("description", "text")])
        
        # Índices para pedidos
        await Order.create_index("user_id")
        await Order.create_index("status")
        await Order.create_index("created_at")
        
        # Índices para carrito
        await CartItem.create_index("user_id")
        await CartItem.create_index([("user_id", 1), ("menu_item_id", 1)], unique=True)
        
        print("📋 Database indexes created successfully!")
        
    except Exception as e:
        print(f"⚠️ Warning: Could not create some indexes: {e}")

async def create_initial_data():
    """Crear datos iniciales si no existen"""
    try:
        from app.models.user import User
        from app.models.category import Category
        from app.core.security import get_password_hash
        from datetime import datetime
        
        # Verificar si ya existe un usuario admin
        admin_user = await User.find_one(User.email == "admin@restaurant.com")
        
        if not admin_user:
            # Crear usuario administrador
            admin_data = User(
                username="admin",
                email="admin@restaurant.com",
                password=get_password_hash("admin123"),
                role="ADMIN",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await admin_data.create()
            print("👤 Admin user created: admin@restaurant.com / admin123")
        
        # Verificar si ya existen categorías
        categories_count = await Category.count()
        
        if categories_count == 0:
            # Crear categorías por defecto
            default_categories = [
                {
                    "name": "Entradas",
                    "description": "Aperitivos y entradas",
                    "active": True
                },
                {
                    "name": "Platos Principales",
                    "description": "Platos principales y carnes",
                    "active": True
                },
                {
                    "name": "Postres",
                    "description": "Postres y dulces",
                    "active": True
                },
                {
                    "name": "Bebidas",
                    "description": "Bebidas y refrescos",
                    "active": True
                }
            ]
            
            for cat_data in default_categories:
                category = Category(
                    name=cat_data["name"],
                    description=cat_data["description"],
                    active=cat_data["active"],
                    created_at=datetime.utcnow()
                )
                await category.create()
            
            print("📂 Default categories created successfully!")
        
    except Exception as e:
        print(f"⚠️ Warning: Could not create initial data: {e}")

def get_database():
    """Obtener instancia de la base de datos"""
    global mongodb_client
    if mongodb_client is None:
        raise Exception("Database not initialized. Call init_db() first.")
    return mongodb_client[settings.database_name]

# Health check para la base de datos
async def ping_database():
    """Verificar que la base de datos esté disponible"""
    try:
        global mongodb_client
        if mongodb_client:
            await mongodb_client.admin.command('ping')
            return True
        return False
    except Exception:
        return False