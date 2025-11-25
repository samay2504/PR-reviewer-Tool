/**
 * Format text utilities - clean markdown and format nicely
 */

/**
 * Strip markdown formatting and return clean text
 * @param {string} text - Text with markdown
 * @returns {string} Clean formatted text
 */
export function stripMarkdown(text) {
  if (!text) return '';
  
  return text
    // Remove markdown bold/italic
    .replace(/\*\*\*(.+?)\*\*\*/g, '$1')  // ***bold italic***
    .replace(/\*\*(.+?)\*\*/g, '$1')       // **bold**
    .replace(/\*(.+?)\*/g, '$1')           // *italic*
    .replace(/__(.+?)__/g, '$1')           // __bold__
    .replace(/_(.+?)_/g, '$1')             // _italic_
    
    // Remove bullet points and list markers
    .replace(/^\s*[-*+]\s+/gm, '• ')       // Convert - * + to bullet
    .replace(/^\s*\d+\.\s+/gm, '')         // Remove numbered lists (1. 2. 3.)
    
    // Remove headers
    .replace(/^#{1,6}\s+/gm, '')           // # ## ### headers
    
    // Remove links but keep text
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // [text](url) -> text
    
    // Remove inline code backticks
    .replace(/`([^`]+)`/g, '$1')           // `code` -> code
    
    // Clean up excessive whitespace
    .replace(/\n{3,}/g, '\n\n')            // Max 2 newlines
    .trim();
}

/**
 * Format summary text into paragraphs
 * @param {string} text - Text to format
 * @returns {Array<string>} Array of paragraphs
 */
export function formatToParagraphs(text) {
  if (!text) return [];
  
  const cleaned = stripMarkdown(text);
  
  // Split by double newlines or section markers
  return cleaned
    .split(/\n\n+/)
    .map(p => p.trim())
    .filter(p => p.length > 0);
}

/**
 * Extract sections from formatted text
 * @param {string} text - Text with sections
 * @returns {Array<Object>} Array of {title, content}
 */
export function extractSections(text) {
  if (!text) return [];
  
  const lines = text.split('\n');
  const sections = [];
  let currentSection = null;
  
  lines.forEach(line => {
    // Detect section headers (lines ending with : or starting with **)
    if (line.trim().endsWith(':') || line.includes('**')) {
      if (currentSection) {
        sections.push(currentSection);
      }
      currentSection = {
        title: stripMarkdown(line.replace(':', '')),
        content: []
      };
    } else if (currentSection && line.trim()) {
      currentSection.content.push(stripMarkdown(line));
    } else if (!currentSection && line.trim()) {
      // Content before any section
      if (!sections.length || sections[0].title !== 'Summary') {
        sections.unshift({
          title: 'Summary',
          content: []
        });
      }
      sections[0].content.push(stripMarkdown(line));
    }
  });
  
  if (currentSection) {
    sections.push(currentSection);
  }
  
  return sections.filter(s => s.content.length > 0);
}
