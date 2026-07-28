from sqlalchemy.orm import Mapped, declarative_base, mapped_column

Base = declarative_base()


class Build(Base):
    __tablename__ = "builds"

    attrpath: Mapped[str] = mapped_column(primary_key=True)
    hydra_id: Mapped[int | None]
    tag: Mapped[str]
    error_line_number: Mapped[int | None]
    last_success_rev: Mapped[str | None]
    last_success_date: Mapped[str | None]
