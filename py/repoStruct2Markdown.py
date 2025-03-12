import os
import pathlib
import re
from typing import List, Optional, Union, Dict, Tuple


def generate_repo_structure_to_markdown(
    path: Union[str, pathlib.Path],
    output_file: Optional[str] = None,
    ignore_patterns: Optional[List[str]] = None,
    ignore_hidden: bool = True,
    include_file_contents: bool = True,
) -> str:
    """
    Generate a markdown-formatted directory structure representation of a repository
    with distinct symbols for folders and files.
    
    This function traverses a directory structure and creates a markdown-formatted
    tree representation, which can either be returned as a string or saved to a file.
    
    Parameters:
    -----------
    path : str or Path
        Path to the repository root directory whose structure should be represented.
    output_file : str, optional
        If provided, the output will be saved to this file. If not, the output
        is returned as a string.
    ignore_patterns : list of str, optional
        List of patterns to ignore. Files and directories matching these patterns 
        will be excluded from the output.
    ignore_hidden : bool, default=True
        Whether to ignore hidden files and directories (those starting with a dot).
    include_file_contents : bool, default=True
        Whether to include file contents as markdown sections after the tree.
        
    Returns:
    --------
    str
        The markdown-formatted directory structure (if output_file is None).
        Otherwise, returns None after writing to the file.
    """
    # Convert to pathlib.Path if it's a string
    directory_path = pathlib.Path(path)
    
    # Define symbols for folders and files
    FOLDER_SYMBOL = "📁"  # Folder emoji
    FILE_SYMBOL = "📄"    # File emoji
    
    result = ["This is a source code repo with markdown formatting.\n"]
    result.append("# Repository Structure")
    result.append(f"We use {FOLDER_SYMBOL} to represent folder, and {FILE_SYMBOL} as file.\n")
    
    # Initialize the result string with the root directory name
    root_name = directory_path.name or str(directory_path)
    # result = [f"- {FOLDER_SYMBOL} {root_name}"]
    result.append(f"- {FOLDER_SYMBOL} {root_name}")
    
    # Dictionary to store file paths and their content
    file_contents: Dict[str, Tuple[str, pathlib.Path, str]] = {}
    
    # Compile regex pattern for hidden files/directories
    hidden_pattern = re.compile(r'^\..*')
    
    # Function to check if an item should be ignored
    def _should_ignore(item):
        # Check if item is hidden and should be ignored
        if ignore_hidden and hidden_pattern.match(item.name):
            return True
            
        # Check against explicit ignore patterns
        if ignore_patterns is None:
            return False
        
        for pattern in ignore_patterns:
            # For exact directory/file names
            if pattern == item.name:
                return True
            
            # For wildcard patterns (e.g., *.pyc)
            if '*' in pattern and item.match(pattern):
                return True
        
        return False
    
    # Define a recursive function to build the tree structure
    def _build_tree(directory: pathlib.Path, prefix: str = "", indent: str = "  "):
        # List all items in the directory
        try:
            items = list(directory.iterdir())
        except PermissionError:
            # Handle permission errors gracefully
            result.append(f"{prefix}{indent}- ⚠️ [Permission denied]")
            return
        
        # Separate and sort directories and files
        dirs = sorted([item for item in items if item.is_dir()], key=lambda x: x.name.lower())
        files = sorted([item for item in items if item.is_file()], key=lambda x: x.name.lower())
        
        # Process all items (directories first, then files)
        for dir_item in dirs:
            # Skip items that should be ignored
            if _should_ignore(dir_item):
                continue
                
            # Add the directory to the tree with folder symbol
            result.append(f"{prefix}{indent}- {FOLDER_SYMBOL} {dir_item.name}")
            
            # Recurse into directories
            _build_tree(dir_item, prefix + indent, indent)
            
        # Process files after directories
        for file_item in files:
            # Skip items that should be ignored or unsupported file types
            if _should_ignore(file_item) or determine_file_language(file_item) is None:
                continue
            
            # Get the relative path from the root directory
            rel_path = file_item.relative_to(directory_path)
            # Create an anchor ID for the file
            anchor_id = create_anchor_id(str(rel_path))
                
            # Add the file to the tree with file symbol
            result.append(f"{prefix}{indent}- {FILE_SYMBOL} [{file_item.name}](#{anchor_id})")
            
            # Store file path, anchor, and relative path for content section generation
            if include_file_contents:
                # Use a tuple including relative path string
                file_contents[str(rel_path)+"//"+file_item.name] = (anchor_id, file_item, str(rel_path))
    
    # Generate the tree starting from the root
    _build_tree(directory_path)
    
    # Add file content sections after the tree if requested
    if include_file_contents and file_contents:
        # Add a separator after the tree
        result.append("\n---\n")
        result.append("# File Contents\n")
        
        # Add each file's content as a section
        for filename, (anchor_id, file_path, rel_path) in file_contents.items():
            language = determine_file_language(file_path)
            assert language is not None, f"File in here should be valid Language extension: {file_path}"
            
            # Create an anchor ID for the file
            # anchor_id = create_anchor_id(str(rel_path))
            # Use the anchor ID as the heading instead of just the relative path
            result.append(f"## {anchor_id}")
            # Add the actual file path for additional context
            result.append(f"file: {rel_path}")
            # Add a descriptive line to help LLMs understand the content that follows
            result.append(f"Here is contents of {rel_path} with line numbers:")
            
            try:
                # Read file content
                content = file_path.read_text(encoding='utf-8', errors='replace')
                
                # Add code fence with language
                fence = f"```{language}"
                result.append(fence)
                
                # Split content into lines, add line numbers, and join back
                content_lines = content.rstrip().split('\n')
                numbered_lines = []
                for i, line in enumerate(content_lines, 1):
                    # Format line with number (like "1: line content")
                    numbered_lines.append(f"{i}: {line}")
                
                # Join the numbered lines and add to result
                result.append('\n'.join(numbered_lines))
                
                result.append("```")
                result.append("---\n")
            except Exception as e:
                result.append(f"*Error reading file: {str(e)}*\n")
    
    
    # Combine all lines into a single string
    markdown_structure = "\n".join(result)
    
    # Print to console
    print(markdown_structure)
    
    # Either save to file or return as string
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_structure)
        print(f"Repository structure saved to {output_file}")
    
    return markdown_structure


# Function to create an anchor ID from a filename
def create_anchor_id(filename):
     # Convert to lowercase and replace non-alphanumeric characters with dashes
    anchor = re.sub(r'[^a-zA-Z0-9]', '-', filename.lower())
    # Remove consecutive dashes
    anchor = re.sub(r'-+', '-', anchor)
    # Remove leading and trailing dashes
    anchor = anchor.strip('-')
    return anchor


# Function to read file contents and return as markdown code block
def determine_file_language(file_path: pathlib.Path) -> Optional[str]:
    """
    Determine the programming language based on file extension.
    
    Parameters:
    -----------
    file_path : pathlib.Path
        Path to the file.
        
    Returns:
    --------
    str or None
        The language name for code highlighting, or None if not recognized.
    """
    # Mapping of file extensions to language names, you can add more extensions here
    extension_map = {
        '.cpp': 'cpp',
        '.c': 'c', 
        '.h': 'cpp',  # Header files typically use C++ syntax highlighting
        '.hpp': 'cpp',
        '.py': 'python',
        '.js': 'javascript',
        '.html': 'html',
        '.css': 'css',
        '.java': 'java',
        '.md': 'markdown',
        '.json': 'json',
        '.xml': 'xml',
        '.sql': 'sql',
        '.sh': 'bash',
        '.bat': 'batch',
        '.ps1': 'powershell',
        '.cs': 'csharp',
        '.rb': 'ruby',
        '.php': 'php',
        '.pl': 'perl',
        '.go': 'go',
        '.rs': 'rust',
        '.idl': 'idl',
        '.yaml': 'yaml',
        # Add more extensions here
    }
    
    suffix = file_path.suffix.lower()
    return extension_map.get(suffix) # Returns None if not found


if __name__ == "__main__":
    import argparse
    
    # Create argument parser
    parser = argparse.ArgumentParser(description='Generate a simplified tree-like markdown representation of a repository structure.')
    parser.add_argument('path', help='Path to the repository root directory')
    parser.add_argument('--output', '-o', help='Output markdown file path')
    parser.add_argument('--ignore', '-i', nargs='+', help='Patterns to ignore (e.g., __pycache__ *.pyc)')
    parser.add_argument('--show-hidden', action='store_true', help='Show hidden files and directories (starting with .)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Call the function with parsed arguments
    result = generate_repo_structure_to_markdown(
        args.path, 
        output_file=args.output,
        ignore_patterns=args.ignore,
        ignore_hidden=not args.show_hidden
    )
    
    # If output wasn't saved to a file, print it to console
    if not args.output and result:
        print(result)
