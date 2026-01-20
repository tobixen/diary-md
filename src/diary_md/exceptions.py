"""Exception classes for diary-md."""


class DiaryParseError(Exception):
    """Detailed error for diary parsing issues."""

    def __init__(
        self,
        message: str,
        file_name: str | None = None,
        file_position: int | None = None,
        section: str | None = None,
        date: str | None = None,
        content: str | None = None,
    ):
        details = [message]
        if file_name:
            details.append(f"  File: {file_name}")
        if file_position is not None:
            details.append(f"  Position: {file_position}")
        if section:
            details.append(f"  Section: {section}")
        if date:
            details.append(f"  Date: {date}")
        if content:
            content_preview = content[:200] + "..." if len(content) > 200 else content
            details.append(f"  Content: {content_preview!r}")
        super().__init__("\n".join(details))

        self.file_name = file_name
        self.file_position = file_position
        self.section = section
        self.date = date
        self.content = content
