import os
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('db_models')

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.warning("DATABASE_URL not found in environment variables, using SQLite")
    DATABASE_URL = "sqlite:///arbitrage.db"

# Create SQLAlchemy engine and session
engine = create_engine(DATABASE_URL)
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

Base = declarative_base()

class Bookmaker(Base):
    """Model for bookmaker information"""
    __tablename__ = 'bookmakers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    url = Column(String(255))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    matches = relationship("Match", back_populates="bookmaker")
    
    def __repr__(self):
        return f"<Bookmaker(name='{self.name}')>"


class Match(Base):
    """Model for match/event information"""
    __tablename__ = 'matches'
    
    id = Column(Integer, primary_key=True)
    match_id = Column(String(50), nullable=False)  # Original ID from the bookmaker
    bookmaker_id = Column(Integer, ForeignKey('bookmakers.id'), nullable=False)
    sport = Column(String(50))
    league = Column(String(100))
    match_name = Column(String(255), nullable=False)
    normalized_match = Column(String(255), nullable=False)
    start_time = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    bookmaker = relationship("Bookmaker", back_populates="matches")
    odds = relationship("Odds", back_populates="match", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Match(match_name='{self.match_name}', bookmaker='{self.bookmaker.name}')>"


class Odds(Base):
    """Model for odds information"""
    __tablename__ = 'odds'
    
    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey('matches.id'), nullable=False)
    outcome_type = Column(String(50), nullable=False)  # 'home', 'draw', 'away', etc.
    outcome_name = Column(String(255), nullable=False)  # Team/player name
    odds_value = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    match = relationship("Match", back_populates="odds")
    
    def __repr__(self):
        return f"<Odds(outcome='{self.outcome_name}', odds={self.odds_value})>"


class ArbitrageOpportunity(Base):
    """Model for arbitrage opportunities"""
    __tablename__ = 'arbitrage_opportunities'
    
    id = Column(Integer, primary_key=True)
    normalized_match = Column(String(255), nullable=False)
    match_name = Column(String(255), nullable=False)
    sport = Column(String(50))
    league = Column(String(100))
    start_time = Column(DateTime)
    profit_percentage = Column(Float, nullable=False)
    investment = Column(Float, nullable=False)
    expected_return = Column(Float, nullable=False)
    bets_json = Column(Text, nullable=False)  # Store bets as JSON
    is_active = Column(Boolean, default=True)
    discovered_at = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<ArbitrageOpportunity(match='{self.match_name}', profit={self.profit_percentage})>"
    
    @property
    def bets(self):
        """Return bets as a list of dictionaries"""
        if self.bets_json:
            return json.loads(self.bets_json)
        return []
    
    @bets.setter
    def bets(self, value):
        """Store bets as a JSON string"""
        self.bets_json = json.dumps(value)


def initialize_db():
    """Create database tables if they don't exist"""
    logger.info("Initializing database tables...")
    Base.metadata.create_all(engine)
    logger.info("Database tables created successfully")


def get_session():
    """Get a database session"""
    return Session()


def close_session(session):
    """Close a database session"""
    session.close()


if __name__ == "__main__":
    # Create tables when the script is run directly
    initialize_db()
    logger.info("Database initialized")