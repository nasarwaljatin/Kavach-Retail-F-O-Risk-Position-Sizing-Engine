from sqlalchemy.orm import Session
from datetime import datetime
from app.models.risk_config import RiskConfig
from app.core.config import settings

def get_all_config(db: Session) -> dict:
    """Retrieve all configuration keys and values as a dictionary."""
    records = db.query(RiskConfig).all()
    config_dict = {}
    for r in records:
        try:
            # Try to convert to float/int where appropriate
            if "." in r.value:
                config_dict[r.key] = float(r.value)
            else:
                config_dict[r.key] = int(r.value)
        except ValueError:
            config_dict[r.key] = r.value
    return config_dict

def get_config_value(db: Session, key: str, default: str = None) -> str:
    """Get value of a single config key."""
    record = db.query(RiskConfig).filter(RiskConfig.key == key).first()
    return record.value if record else default

def set_config_value(db: Session, key: str, value: str) -> RiskConfig:
    """Set the value of a config key, updating it if it exists, creating it if not."""
    record = db.query(RiskConfig).filter(RiskConfig.key == key).first()
    if record:
        record.value = str(value)
        record.updated_at = datetime.utcnow()
    else:
        record = RiskConfig(key=key, value=str(value))
        db.add(record)
    db.commit()
    db.refresh(record)
    return record

def initialize_defaults(db: Session) -> None:
    """Seed the database with default configuration from env settings if empty."""
    defaults = {
        "MAX_DAILY_LOSS_PCT": str(settings.MAX_DAILY_LOSS_PCT),
        "MAX_POSITION_CONCENTRATION_PCT": str(settings.MAX_POSITION_CONCENTRATION_PCT),
        "MAX_MARGIN_UTILISATION_PCT": str(settings.MAX_MARGIN_UTILISATION_PCT),
        "KELLY_FRACTION_MULTIPLIER": str(settings.KELLY_FRACTION_MULTIPLIER),
        "ORDER_VELOCITY_LIMIT_PER_10MIN": str(settings.ORDER_VELOCITY_LIMIT_PER_10MIN),
        "EXPIRY_DAY_SIZE_DAMPENER": str(settings.EXPIRY_DAY_SIZE_DAMPENER),
    }
    
    for key, value in defaults.items():
        existing = db.query(RiskConfig).filter(RiskConfig.key == key).first()
        if not existing:
            db.add(RiskConfig(key=key, value=value))
    db.commit()
