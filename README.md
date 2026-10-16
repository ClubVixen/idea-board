# Idea Board

A desktop corkboard for collecting ideas: pin notes and images, attach sticky notes to images, and link them with red string. Built with Python and PySide6.

## Run

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Using the board

- **Add Note / Add Image** from the toolbar, or right-click the board for **Add New Note**. You can also drag image files onto the board.
- Hover a note or image for its buttons: **L** link to another item, **X** delete, **C** crop an image, **N** add a sticky note to an image.
- Drag the round handle under an item to rotate it; drag the corner handle of an image to resize it.
- Click a note's text to open the full text in the side panel. Click the empty board to close it.
- Mouse wheel zooms the board, or scrolls a note's text when hovering a long note. Middle-drag pans.
- **Save / Load** boards as `.json`, or **Export PNG** to share an image of the board.
