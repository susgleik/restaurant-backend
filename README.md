# 🍽️ Restaurant App Backend

This project is the backend for a restaurant application, built with **FastAPI** and **MongoDB**.  
It is currently deployed on [Render.com](https://render.com).  

The backend follows a conventional **FastAPI** project structure and uses an **ODM** for creating collections.  
We use **Pydantic** for data validation and serialization, and **Azure Blob Storage** for managing and serving uploaded images.

---
## 📂 API Structure
The backend provides five main groups of endpoints:

- **`/menu_items`**  
  Handles CRUD operations for menu items, such as chicken curry, Coca-Cola, spaghetti, etc.

- **`/auth`**  
  Authentication endpoints for login and registration.

- **`/cart`**  
  Manages shopping cart data: adding, removing, and updating items.

- **`/categories`**  
  Manages menu categories, such as soups, meats, beverages, etc.

- **`/orders`**  
  Handles order logic, including creation and status updates (in preparation, ready, delivered, etc.).

---
## 🚀 Getting Started

### 📋 Prerequisites
Make sure you have the following installed:
- **Docker** and **Docker Compose**
- A **MongoDB** database connection URL
- An **Azure Blob Storage** connection string

---

### ▶️ Running the Application
To start the application, run:

```bash
docker-compose up --build
```
