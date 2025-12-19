"""
Text parser for Star Valor game text files.
Parses the game text format and extracts translatable entries.
"""
import re


class TextEntry:
    """Represents a single text entry to be translated."""
    
    def __init__(self, classname, classid, no, orig_text, trans_text=""):
        self.classname = classname
        self.classid = classid
        self.no = no
        self.orig_text = orig_text
        self.trans_text = trans_text
    
    def __repr__(self):
        return f"TextEntry({self.classname}, {self.classid}, {self.no}, {self.orig_text})"


class TextParser:
    """Parser for Star Valor text files."""
    
    def __init__(self):
        self.entries = []
        
    def parse_file(self, filepath):
        """
        Parse a text file and extract all translatable entries.
        
        Args:
            filepath: Path to the text file to parse
            
        Returns:
            List of TextEntry objects
        """
        self.entries = []
        current_classname = None
        current_classid = None
        
        # Read entire file at once for better performance
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        i = 0
        
        while i < len(lines):
            line = lines[i].rstrip('\n')
            
            # Check for class section header: [0] Basic/Fixed UI    |
            class_match = re.match(r'\[(\d+)\]\s+(.+?)\s*\|', line)
            if class_match:
                current_classid = int(class_match.group(1))
                current_classname = class_match.group(2).strip()
                i += 1
                continue
            
            # Check for numbered entry start: 000 Loading|
            # This may be a single line or multi-line entry
            entry_match = re.match(r'(\d{3})\s+(.*)', line)
            if entry_match and current_classname is not None:
                no = entry_match.group(1)
                text_part = entry_match.group(2)
                
                # Check if this line ends with |
                if text_part.endswith('|'):
                    # Single line entry
                    orig_text = text_part[:-1].strip()  # Remove the | and strip
                else:
                    # Multi-line entry - collect lines until we find one ending with |
                    text_lines = [text_part]
                    i += 1
                    while i < len(lines):
                        next_line = lines[i].rstrip('\n')
                        text_lines.append(next_line)
                        if next_line.endswith('|'):
                            break
                        i += 1
                    
                    # Join all lines and remove the final |
                    orig_text = '\n'.join(text_lines)
                    if orig_text.endswith('|'):
                        orig_text = orig_text[:-1].strip()
                    # If no terminating | was found, still use the collected text
                
                entry = TextEntry(
                    classname=current_classname,
                    classid=current_classid,
                    no=no,
                    orig_text=orig_text
                )
                self.entries.append(entry)
                i += 1
                continue
            
            i += 1
        
        return self.entries
    
    def export_to_file(self, entries, filepath):
        """
        Export entries back to text file format.
        
        Args:
            entries: List of TextEntry objects
            filepath: Output file path
        """
        # Group entries by classid and classname
        grouped = {}
        for entry in entries:
            key = (entry.classid, entry.classname)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(entry)
        
        # Sort by classid
        sorted_groups = sorted(grouped.items(), key=lambda x: x[0][0])
        
        with open(filepath, 'w', encoding='utf-8') as f:
            for (classid, classname), group_entries in sorted_groups:
                # Write section header
                f.write("#=============|\n")
                f.write(f"[{classid}] {classname.ljust(18)}|\n")
                f.write("#=============|\n")
                
                # Sort entries by no within the group
                group_entries.sort(key=lambda e: e.no)
                
                # Write entries
                for entry in group_entries:
                    # Use translated text if available, otherwise original
                    text = entry.trans_text if entry.trans_text else entry.orig_text
                    
                    # Check if text contains newlines (multi-line entry)
                    if '\n' in text:
                        # Multi-line entry: first line has the number, subsequent lines don't
                        # The last line should end with |
                        lines = text.split('\n')
                        f.write(f"{entry.no} {lines[0]}\n")
                        for idx in range(1, len(lines)):
                            if idx == len(lines) - 1:
                                # Last line gets the |
                                f.write(f"{lines[idx]}|\n")
                            else:
                                f.write(f"{lines[idx]}\n")
                    else:
                        # Single-line entry
                        f.write(f"{entry.no} {text}|\n")
