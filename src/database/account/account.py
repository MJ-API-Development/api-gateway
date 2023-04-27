import hashlib
import secrets

from pydantic import BaseModel
from sqlalchemy import Column, String, inspect, Boolean
from sqlalchemy.orm import relationship

from src.authorize.authorize import NotAuthorized
from src.const import UUID_LEN, NAME_LEN, EMAIL_LEN, STR_LEN, CELL_LEN
from src.database.apikeys.keys import ApiKeyModel
from src.database.database_sessions import Base, sessionType, engine
from src.utils.utils import create_id


class TwoFactorLoginData(BaseModel):
    email: str
    code: str


class Account(Base):
    """
        User Account ORM
    """
    __tablename__ = "accounts"
    uuid: str = Column(String(UUID_LEN), primary_key=True, index=True)
    first_name: str = Column(String(NAME_LEN), index=True)
    second_name: str = Column(String(NAME_LEN), index=True)
    surname: str = Column(String(NAME_LEN), index=True)
    email: str = Column(String(EMAIL_LEN), index=True, unique=True)
    cell: str = Column(String(CELL_LEN), index=True, unique=True)
    password_hash: str = Column(String(STR_LEN), index=True)
    is_admin: bool = Column(Boolean, default=False)
    is_deleted: bool = Column(Boolean, default=False)
    apikey = relationship('ApiKeyModel', uselist=False, foreign_keys=[ApiKeyModel.uuid])

    def __init__(self, uuid: str, first_name: str, second_name: str, surname: str, email: str, cell: str,
                 password: str):
        self.uuid = uuid or create_id()
        self.first_name = first_name
        self.second_name = second_name
        self.surname = surname
        self.email = email
        self.cell = cell
        self.password = password

    def __bool__(self) -> bool:
        return bool(self.uuid)

    @classmethod
    def create_if_not_exists(cls):
        if not inspect(engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=engine)

    @property
    def names(self) -> str:
        return f"{self.first_name}, {self.second_name}, {self.surname}"

    @property
    def contact_details(self) -> str:
        return f"Cell: {self.cell}, Email: {self.email}"

    @property
    def password(self) -> str:
        """
        Raises an AttributeError if someone tries to get the password directly
        """
        return self.password_hash

    @password.setter
    def password(self, plaintext_password: str) -> None:
        """
        Hashes and sets the user's password
        """
        self.password_hash = hashlib.sha256(plaintext_password.encode('utf-8')).hexdigest()

    def to_dict(self) -> dict[str, str]:
        init_dict = {
            "uuid": self.uuid,
            "first_name": self.first_name,
            "second_name": self.second_name,
            "surname": self.surname,
            "email": self.email,
            "cell": self.cell,
            "is_admin": self.is_admin
        }
        if self.apikey:
            init_dict["apikey"] = self.apikey.to_dict()
        return init_dict

    @classmethod
    async def get_by_uuid(cls, uuid: str, session: sessionType):
        return session.query(cls).filter(cls.uuid == uuid).first()

    @classmethod
    async def get_by_email(cls, email: str, session: sessionType):
        return session.query(cls).filter(cls.email == email).first()

    @classmethod
    async def login(cls, username: str, password: str, session: sessionType):
        # Get the user with the specified email address
        user: Account = session.query(cls).filter(cls.email == username.casefold()).first()

        if (user is None) or user.is_deleted:
            raise NotAuthorized(message="You are not authorized to login to this account")

        # Hash the entered password using a secure hash function (SHA-256 in this example)
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        # Compare the hashed password to the stored hash using secrets.compare_digest,
        # and return either the user object or None depending on the result
        return user if user and secrets.compare_digest(password_hash, user.password) else None

    @classmethod
    async def fetch_all(cls, session: sessionType) -> list[any]:
        """
            Returns a complete list of users
        :param session:
        :return:
        """
        return session.query(cls).all()
