"""Progress indicators"""
from __future__ import annotations

import sys
import time
from typing import TextIO


class ProgressBar:
    """Simple progress bar"""
    
    def __init__(
        self,
        total: int,
        width: int = 50,
        fill: str = "█",
        empty: str = "░",
        stream: TextIO = sys.stdout,
    ):
        self.total = total
        self.width = width
        self.fill = fill
        self.empty = empty
        self.stream = stream
        self.current = 0
        self.start_time = time.time()
    
    def update(self, current: int | None = None) -> None:
        """Update progress"""
        if current is not None:
            self.current = current
        else:
            self.current += 1
        
        # Calculate percentage
        percent = self.current / self.total if self.total > 0 else 0
        
        # Calculate filled width
        filled_width = int(self.width * percent)
        
        # Build bar
        bar = self.fill * filled_width + self.empty * (self.width - filled_width)
        
        # Calculate ETA
        elapsed = time.time() - self.start_time
        if self.current > 0:
            eta = (elapsed / self.current) * (self.total - self.current)
            eta_str = f"ETA: {eta:.1f}s"
        else:
            eta_str = "ETA: --"
        
        # Print
        self.stream.write(f"\r[{bar}] {percent:.1%} {eta_str}")
        self.stream.flush()
    
    def finish(self) -> None:
        """Finish progress bar"""
        self.stream.write("\n")
        self.stream.flush()


class Spinner:
    """Simple spinner"""
    
    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    
    def __init__(self, text: str = "", stream: TextIO = sys.stdout):
        self.text = text
        self.stream = stream
        self.frame = 0
    
    def update(self, text: str | None = None) -> None:
        """Update spinner"""
        if text is not None:
            self.text = text
        
        frame = self.FRAMES[self.frame % len(self.FRAMES)]
        self.stream.write(f"\r{frame} {self.text}")
        self.stream.flush()
        
        self.frame += 1
    
    def finish(self, final_text: str = "Done") -> None:
        """Finish spinner"""
        self.stream.write(f"\r✓ {final_text}\n")
        self.stream.flush()
