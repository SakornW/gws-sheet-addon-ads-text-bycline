from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.db.models import AdGeneration, Product, ScrapedData, User


# User CRUD operations
def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, username: str, email: str, password: str) -> User:
    hashed_password = get_password_hash(password)
    db_user = User(username=username, email=email, password_hash=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


# Product CRUD operations
def get_product(db: Session, product_id: int) -> Optional[Product]:
    return db.query(Product).filter(Product.id == product_id).first()


def get_products_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Product]:
    return db.query(Product).filter(Product.user_id == user_id).offset(skip).limit(limit).all()


def create_product(db: Session, user_id: int, name: str, description: Optional[str] = None,
                   specifications: Optional[str] = None, cta_link: Optional[str] = None) -> Product:
    db_product = Product(
        user_id=user_id,
        name=name,
        description=description,
        specifications=specifications,
        cta_link=cta_link
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


# ScrapedData CRUD operations
def create_scraped_data(db: Session, product_id: int, source_url: str,
                        content: str, relevance_score: float) -> ScrapedData:
    db_scraped_data = ScrapedData(
        product_id=product_id,
        source_url=source_url,
        content=content,
        relevance_score=relevance_score
    )
    db.add(db_scraped_data)
    db.commit()
    db.refresh(db_scraped_data)
    return db_scraped_data


def get_scraped_data_by_product(db: Session, product_id: int) -> List[ScrapedData]:
    return db.query(ScrapedData).filter(ScrapedData.product_id == product_id).all()


# AdGeneration CRUD operations
def create_ad_generation(db: Session, user_id: int, product_id: int,
                         generated_text: str, generation_params: Dict[str, Any],
                         platform: str = "Facebook") -> AdGeneration:
    db_ad_generation = AdGeneration(
        user_id=user_id,
        product_id=product_id,
        generated_text=generated_text,
        generation_params=generation_params,
        platform=platform
    )
    db.add(db_ad_generation)
    db.commit()
    db.refresh(db_ad_generation)
    return db_ad_generation


def get_ad_generations_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[AdGeneration]:
    return db.query(AdGeneration).filter(AdGeneration.user_id == user_id).offset(skip).limit(limit).all()


def get_ad_generations_by_product(db: Session, product_id: int) -> List[AdGeneration]:
    return db.query(AdGeneration).filter(AdGeneration.product_id == product_id).all()
