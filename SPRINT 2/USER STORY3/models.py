from sqlalchemy import create_engine, Column, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./feedback.db"

engine = create_engine(
    DATABASE_URL,
    echo=True,  
)

Base = declarative_base()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Feedback(Base):
    __tablename__ = "feedbacks"

    feedback_id = Column(String, primary_key=True, index=True) 
    prediction_id = Column(String, index=True)                  
    feedback_text = Column(Text, nullable=True)                 
    rating = Column(String, nullable=True)                      
    user_id = Column(String, nullable=True)                     

Base.metadata.create_all(bind=engine)
