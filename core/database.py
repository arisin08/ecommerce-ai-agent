from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Mapped, mapped_column
from sqlalchemy import String, Integer , Float, Boolean, select
from config import DATABASE_URL


#creating a connector between database and codefile 
engine = create_async_engine(DATABASE_URL, echo= True) # flip echo to True for debug , False for production mode

#creating a session using the above engine 
AsyncSessionLocal = sessionmaker(engine, class_= AsyncSession, expire_on_commit= False)


class Base(DeclarativeBase):
    pass

class Product(Base):
    __tablename__ = "products"

    #field_name: Mapped[python_type] = mapped_column(SQLType, options)
    id : Mapped[str] = mapped_column(String, primary_key=True)
    name : Mapped[str] = mapped_column(String, nullable=False)
    category : Mapped[str] = mapped_column(String)
    description : Mapped[str] = mapped_column(String)
    quantity : Mapped[int] = mapped_column(Integer, default= 0)
    unit_price : Mapped[float] = mapped_column(Float)
    max_stock : Mapped[int] = mapped_column(Integer, default=100)
    is_active : Mapped[bool] = mapped_column(Boolean, default=True)


#Function which creates table in database file 
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("###### Database Initialized #######")


#Ingesting product catalogue of e-commerce store
async def seed_products():
    async with AsyncSessionLocal() as session: 
        #guard skip if already seeded
        result = await session.execute(select(Product))
        existing = result.scalars().all()
        if existing: 
            print("Products already seeded ")
            return 


        gaming_laptop = Product(id = "P001",
                                name = "Gaming Laptop Pro",
                                category = "laptop",
                                description = "High Performance gaming laptop RTX 4070 16gb RAM",
                                quantity = 45,
                                unit_price = 130000,
                                max_stock = 50
                                )
        
        budget_laptop = Product(id = "P002",
                                name = "Budget Laptop Pro",
                                category = "laptop",
                                description = "Mid Performance laptop with 4gb RAM and i5 processor",
                                quantity = 60,
                                unit_price = 70000,
                                max_stock = 50
                                )  
        
        keyboard = Product(id = "P003",
                            name = "Kreo Hive",
                            category = "Keyboard",
                            description = "Mechanical keyboard white with yellow switches",
                            quantity = 30,
                            unit_price = 5000,
                            max_stock = 50
                            )  
        
        
        mouse = Product(id = "P004",
                        name = "Logitech MX4",
                        category = "Mouse",
                        description = "Mouse with 8k DPI and haptic feedback",
                        quantity = 3,
                        unit_price = 7000,
                        max_stock = 50
                        ) 
        
        monitor = Product(id = "P005",
                        name = "LG P11",
                        category = "Monitor",
                        description = "Monitor 27 inch with 2k resolution and 165 hz refresh rate",
                        quantity = 0,
                        unit_price = 21000,
                        max_stock = 50
                        ) 


        session.add_all([gaming_laptop, budget_laptop, keyboard, mouse, monitor])
        await session.commit()
        print("########## Products Seeded #############")
