import fitz 
import json


class PDFWord:
    """Represents a word (or span) extracted from a PDF page."""
    def __init__(self, span, line):
        color = span["color"]
        self.text = span["text"]
        self.left = span["bbox"][0]
        self.top = line["bbox"][1]
        self.width = span["bbox"][2] - span["bbox"][0]
        self.height = span["bbox"][3] - line["bbox"][1]
        self.font = span["font"]
        self.size = span["size"]
        self.r = (color >> 16) & 0xFF
        self.g = (color >> 8) & 0xFF
        self.b = color & 0xFF
        self.line_no = line["bbox"][1]

        # flags
        self.is_header = False
        self.is_anchor = False
        self.is_anchor_value = False
        self.is_table_word = False
        self.header = None
        self.token = {}

    def to_dict(self):
        return {
            "text": self.text,
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
            "font": self.font,
            "size": self.size,
            "r": self.r,
            "g": self.g,
            "b": self.b,
            "line_no": self.line_no,
            "is_header": self.is_header,
            "is_anchor": self.is_anchor,
            "is_anchor_value": self.is_anchor_value,
            "is_table_word": self.is_table_word,
            "header": self.header,
            "token": self.token
        }


class PDFPageParser:
    """Parses a single PDF page into structured words and headers."""
    HEADER_KEYWORDS = ["Date", "Date de Valeur", "Opération", "Débit", "Crédit"]

    def __init__(self, page, global_column_ranges=None):
        self.page = page
        self.words = []
        self.header_positions = []
        self.header_groups = {}
        self.global_column_ranges = global_column_ranges
        self.anchors = []
        self.anchor_values = []

    def extract_words(self):
        """Extract text spans and convert them into PDFWord objects."""
        blocks = self.page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    self.words.append(PDFWord(span, line))

    def detect_headers(self):
        """Identify header words and store their positions."""
        for w in self.words:
            if w.text in self.HEADER_KEYWORDS:
                w.is_header = True
                self.header_positions.append({"text": w.text, "x": w.left, "y": w.top, "width": w.width})
                if w.text not in self.header_groups:
                    self.header_groups[w.text] = []
                self.header_groups[w.text].append({
                    "text": w.text,
                    "x": w.left,
                    "y": w.top,
                    "width": w.width,
                    "height": w.height,
                    "font": w.font,
                    "size": w.size,
                    "color": f"rgb({w.r},{w.g},{w.b})"
                })
                w.token = json.dumps(self.header_groups[w.text][-1])
                w.header = w.text

    def detect_column_boundaries(self):
        """Detect column boundaries from table data on this page."""
        if not self.header_positions:
            return None

        header_line_y = min(h["y"] for h in self.header_positions)
        table_zone_y = header_line_y + 25

        # Analyze the actual table data to find column boundaries
        table_words = [w for w in self.words if w.line_no > table_zone_y and not w.is_header]
        
        # Group words by line to find column patterns
        lines = {}
        for w in table_words:
            if w.line_no not in lines:
                lines[w.line_no] = []
            lines[w.line_no].append(w)
        
        # Find typical x-positions for each column by analyzing multiple lines
        column_x_positions = []
        for line_no, words_in_line in lines.items():
            if len(words_in_line) >= 3:  # Only consider lines with multiple words
                sorted_words = sorted(words_in_line, key=lambda w: w.left)
                for i, word in enumerate(sorted_words):
                    if i >= len(column_x_positions):
                        column_x_positions.append([])
                    column_x_positions[i].append(word.left)
        
        # Calculate average x-position for each column
        if not column_x_positions:
            return None
            
        avg_column_x = [sum(positions) / len(positions) for positions in column_x_positions if positions]
        
        # Sort headers by x-position
        sorted_headers = sorted(self.header_positions, key=lambda h: h["x"])
        
        # Create column boundaries based on detected columns
        column_ranges = []
        for i, avg_x in enumerate(avg_column_x):
            if i < len(sorted_headers):
                header = sorted_headers[i]
            else:
                # If we have more data columns than headers
                header_names = ["Date", "Date de Valeur", "Opération", "Débit", "Crédit", "Extra"]
                header = {"text": header_names[i] if i < len(header_names) else f"Column_{i+1}"}
            
            if i < len(avg_column_x) - 1:
                start_x = avg_x - 15
                end_x = avg_column_x[i + 1] - 15
            else:
                start_x = avg_x - 15
                end_x = self.page.rect.width
            
            column_ranges.append({
                "header": header["text"],
                "start_x": start_x,
                "end_x": end_x
            })
        
        return column_ranges

    def _find_table_end(self, table_zone_y):
        """Find where the table ends to exclude text after the table."""
        # Get all unique line numbers sorted
        all_lines = sorted(list(set(w.line_no for w in self.words)))
        
        # Find lines that are part of the table
        table_lines = []
        for line_y in all_lines:
            if line_y < table_zone_y:
                continue
                
            words_in_line = [w for w in self.words if w.line_no == line_y]
            if not words_in_line:
                continue
                
            # Check if this line looks like table data
            is_table_line = False
            for w in words_in_line:
                # Table lines typically have numbers, dates, or specific patterns
                if (any(c.isdigit() for c in w.text) or 
                    '/' in w.text or 
                    '.' in w.text or
                    '€' in w.text or
                    ',' in w.text):
                    is_table_line = True
                    break
            
            if is_table_line:
                table_lines.append(line_y)
            elif table_lines: 
                break
        
        
        if table_lines:
            return max(table_lines) + 10
        else:
            return table_zone_y + 100  

    def _get_credit_column_position(self):
        """Find the exact x-position of the Crédit column header."""
        for header in self.header_positions:
            if header["text"] == "Crédit":
                return header["x"]
        return None

    def assign_headers_to_words(self, column_ranges=None):
        """Assign headers to table words based on column positions."""
        
        if not self.header_positions:
            return

        header_line_y = min(h["y"] for h in self.header_positions)
        
        
        for w in self.words:
            if "ANCIEN SOLDE CRÉDITEUR" in w.text or "SOLDE" in w.text:
                # Look for numeric values on the same line or next line that should be credits
                same_line_words = [word for word in self.words if word.line_no == w.line_no]
                for word in same_line_words:
                    if any(c in "," or c in "€" for c in word.text) and any(c.isdigit() for c in word.text):
                        word.is_anchor_value = True
                        word.header = "Anchor Value"
                        self.anchor_values.append(word)
                        print(f"DEBUG: Found Anchor Value '{word.text}' for ANCIEN SOLDE at X:{word.left:.1f}")

        anchor_line_y = header_line_y + 20
        table_zone_y = anchor_line_y + 5
        
        # Find where the table ends to exclude text after the table
        table_end_y = self._find_table_end(table_zone_y)

        
        if column_ranges is None:
            column_ranges = self.detect_column_boundaries()
        
        
        if not column_ranges:
            sorted_headers = sorted(self.header_positions, key=lambda h: h["x"])
            column_ranges = []
            for i, header in enumerate(sorted_headers):
                if i < len(sorted_headers) - 1:
                    column_ranges.append({
                        "header": header["text"],
                        "start_x": header["x"],
                        "end_x": sorted_headers[i + 1]["x"]
                    })
                else:
                    column_ranges.append({
                        "header": header["text"],
                        "start_x": header["x"],
                        "end_x": self.page.rect.width
                    })

        def get_column_header(word_left, word_text=""):
            """Find which column the word belongs to based on its x-position."""
            for column in column_ranges:
                if column["start_x"] <= word_left < column["end_x"]:
                    return column["header"]
            
            
            closest_col = min(column_ranges, key=lambda col: abs(word_left - col["start_x"]))
            return closest_col["header"]

        
        print(f"DEBUG: Column ranges for anchor assignment:")
        for i, col in enumerate(column_ranges):
            print(f"  Column {i}: '{col['header']}' from {col['start_x']:.1f} to {col['end_x']:.1f}")

       
        credit_x = self._get_credit_column_position()
        print(f"DEBUG: Crédit header position: X={credit_x}")

        # Assign anchors 
        for w in self.words:
            if anchor_line_y - 5 <= w.line_no <= anchor_line_y + 5:
                if any(c in "," or c in "€" for c in w.text):
                    w.is_anchor_value = True
                    nearest_header = get_column_header(w.left, w.text)
                    
                   
                    if credit_x and abs(w.left - credit_x) < 50:  # Within 50 pixels of Crédit header
                        nearest_header = "Crédit"
                        print(f"DEBUG: FORCED '{w.text}' to Crédit column (close to header)")
                    
                    print(f"DEBUG: Anchor Value '{w.text}' at X:{w.left:.1f} assigned to '{nearest_header}'")
                    
                    w.header = f"Anchor Value ({nearest_header})"
                    self.anchor_values.append(w)
                else:
                    w.is_anchor = True
                    w.header = "Anchor"
                    self.anchors.append(w)
                
                w.token = json.dumps({**w.to_dict(), "type": w.header})

        
        for w in self.words:
            if table_zone_y < w.line_no < table_end_y:
                w.is_table_word = True
                w.header = get_column_header(w.left, w.text)
                w.token = json.dumps({**w.to_dict(), "type": w.header})

    def parse(self, column_ranges=None):
        """Full page parsing pipeline."""
        self.extract_words()
        self.detect_headers()
        self.assign_headers_to_words(column_ranges)
        return {
            "width": self.page.rect.width,
            "height": self.page.rect.height,
            "words": [w.to_dict() for w in self.words],
            "header_groups": self.header_groups,
            "anchors": [w.to_dict() for w in self.anchors],
            "anchor_values": [w.to_dict() for w in self.anchor_values]
        }


class PDFParser:
    """High-level PDF parser handling multiple pages."""
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.pages = []
        self.header_groups = {}
        self.global_column_ranges = None

    def parse(self):
        with fitz.open(self.pdf_path) as doc:
            
            for page_num, page in enumerate(doc, start=1):
                parser = PDFPageParser(page)
                page_data = parser.parse()
                
                
                if self.global_column_ranges is None and parser.header_positions:
                    self.global_column_ranges = parser.detect_column_boundaries()
                    print(f"DEBUG: Detected global column ranges from page {page_num}")
                    if self.global_column_ranges:
                        for i, col in enumerate(self.global_column_ranges):
                            print(f"  Column {i+1}: '{col['header']}' from {col['start_x']:.1f} to {col['end_x']:.1f}")
                    break
            
           
            doc = fitz.open(self.pdf_path)  # Reopen to start from beginning
            for page_num, page in enumerate(doc, start=1):
                print(f"Parsing page {page_num} with global column boundaries")
                parser = PDFPageParser(page)
                page_data = parser.parse(self.global_column_ranges)
                self.pages.append({
                    "num": page_num,
                    **page_data
                })
                self.header_groups.update(page_data["header_groups"])
        
        return self.pages, self.header_groups