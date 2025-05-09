from sqlalchemy import (JSON, Boolean, Column, DateTime, Float, ForeignKey,
                        Integer, String, Text)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    products = relationship("Product", back_populates="user")
    ad_generations = relationship("AdGeneration", back_populates="user")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    description = Column(Text, nullable=True)
    specifications = Column(Text, nullable=True)
    cta_link = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="products")
    scraped_data = relationship("ScrapedData", back_populates="product")
    ad_generations = relationship("AdGeneration", back_populates="product")


class ScrapedData(Base):
    __tablename__ = "scraped_data"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    source_url = Column(String)
    content = Column(Text)
    relevance_score = Column(Float)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="scraped_data")


class AdGeneration(Base):
    __tablename__ = "ad_generations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    generated_text = Column(Text)
    generation_params = Column(JSON)
    platform = Column(String, default="Facebook")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="ad_generations")
    product = relationship("Product", back_populates="ad_generations")
