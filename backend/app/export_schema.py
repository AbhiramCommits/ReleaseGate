from pathlib import Path

from app.graphql import schema

TARGET = Path(__file__).resolve().parent.parent / "schema.graphql"


def main() -> None:
    TARGET.write_text(schema.as_str() + "\n")
    print(f"Wrote {TARGET}")


if __name__ == "__main__":
    main()
