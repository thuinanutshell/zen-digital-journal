from flask import Flask
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, declared_attr, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, ForeignKey, DateTime, Text
from datetime import datetime
import json

class Base(DeclarativeBase):
    """Define Base class from which all sub-classes are inherited from
    This helps customize the model classes by adding shared columns,
    attributed or configurations.
    """
    
    # Shared static columns related to datetime for all tables
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    
    # Add a decorator to define class-level attributes that need to be dynamically generated for each subclass, 
    # which ensures that each subclass has its own unique version of the attribute
    # cls is the placeholder for the actual class names such as User, Journal.
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
    
    @declared_attr
    def id(cls) -> Mapped[int]:
        return mapped_column(Integer, primary_key=True)

# Create an instance of SQLAlchemy extension
# All models will inherit from the Base class
db = SQLAlchemy(model_class=Base)
    
class User(db.Model, UserMixin):
    """Define the table model that stores user's personal information
    This model has a one-to-many relationship with the Journal model
    where one user can have multiple entries.
    
    cascade="all, delete-orphan" means when we apply standard operations
    (add, update, delete) to a parent object, they are applied to the child objects.
    delete-orphan means when child objects are removed from parent's collection (orphaned),
    they are automatically deleted from the database.

    Args:
        db: model instance
        UserMixin (class):
            - A class with default implementations for essential properties/methods
            - Automatic methods: is_authenticated, is_active, is_anonymous, get_id()
    """
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    password: Mapped[str] = mapped_column(String(128), nullable=False)
    
    # Attributes for tracking streak
    last_activity_date: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships with the journal entries and the conversations
    entry = relationship("Journal", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")

class Journal(db.Model):
    """Define the table model that stores user's journal entries
    back_populates explicitly defines a bidirectional relationship between 
    the User and the Journal models. This means changes on one side is reflected
    on the other side.

    Args:
        db: model instance
    """
    prompt: Mapped[str] = mapped_column(String(255), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    modality: Mapped[str] = mapped_column(String(20), default='text')
    tag: Mapped[str] = mapped_column(String(150), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'), nullable=False, index=True)
    user = relationship("User", back_populates="entry")

class Conversation(db.Model):
    chat: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'), nullable=False, index=True)
    user = relationship("User", back_populates="conversations")
    
    def get_chat_data(self):
        if not self.chat:
            return []
        try:
            return json.loads(self.chat)
        except json.JSONDecodeError:
            return []
    
    def set_chat_data(self, data):
        self.chat = json.dumps(data)