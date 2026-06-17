import os
import zipfile
import xml.etree.ElementTree as ET

def docx_to_markdown(docx_path, md_path):
    print(f"Reading {docx_path}...")
    if not os.path.exists(docx_path):
        print(f"Error: {docx_path} not found.")
        return False
        
    namespaces = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    }
    
    try:
        with zipfile.ZipFile(docx_path) as docx:
            xml_content = docx.read('word/document.xml')
            root = ET.fromstring(xml_content)
            
            markdown_lines = []
            for p in root.findall('.//w:p', namespaces):
                # Get paragraph style if any
                style_elem = p.find('.//w:pPr/w:pStyle', namespaces)
                style = None
                if style_elem is not None:
                    style = style_elem.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')
                
                # Check list item properties
                num_pr = p.find('.//w:pPr/w:numPr', namespaces)
                is_list = num_pr is not None
                
                # Extract runs of text
                text_runs = []
                for r in p.findall('.//w:r', namespaces):
                    is_bold = r.find('.//w:b', namespaces) is not None
                    is_italic = r.find('.//w:i', namespaces) is not None
                    
                    t_elems = r.findall('.//w:t', namespaces)
                    run_text = "".join([t.text for t in t_elems if t.text])
                    
                    if run_text:
                        if is_bold and is_italic:
                            run_text = f"***{run_text}***"
                        elif is_bold:
                            run_text = f"**{run_text}**"
                        elif is_italic:
                            run_text = f"*{run_text}*"
                        text_runs.append(run_text)
                
                p_text = "".join(text_runs).strip()
                
                if not p_text:
                    # Keep empty lines
                    markdown_lines.append("")
                    continue
                
                # Format headers based on style
                if style:
                    if 'Heading1' in style or style == '1' or style == 'Heading1Char':
                        markdown_lines.append(f"\n# {p_text}\n")
                    elif 'Heading2' in style or style == '2' or style == 'Heading2Char':
                        markdown_lines.append(f"\n## {p_text}\n")
                    elif 'Heading3' in style or style == '3' or style == 'Heading3Char':
                        markdown_lines.append(f"\n### {p_text}\n")
                    elif 'Heading4' in style or style == '4' or style == 'Heading4Char':
                        markdown_lines.append(f"\n#### {p_text}\n")
                    else:
                        if is_list:
                            markdown_lines.append(f"- {p_text}")
                        else:
                            markdown_lines.append(p_text)
                else:
                    if is_list:
                        markdown_lines.append(f"- {p_text}")
                    else:
                        markdown_lines.append(p_text)
            
            # Ensure target directory exists
            os.makedirs(os.path.dirname(md_path), exist_ok=True)
            
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(markdown_lines))
                
            print(f"Successfully exported to {md_path}")
            return True
            
    except Exception as e:
        print(f"Error reading docx: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    # Adjust paths
    docx_file = 'TCC-Kelvin-Albuquerque-ANBT.docx'
    markdown_output = 'docs/TCC_draft.md'
    docx_to_markdown(docx_file, markdown_output)
