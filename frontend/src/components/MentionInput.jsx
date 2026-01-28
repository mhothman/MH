import { useState, useRef, useEffect, useCallback } from 'react';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
import { Textarea } from './ui/textarea';
import { ScrollArea } from './ui/scroll-area';
import { cn } from '../lib/utils';

/**
 * MentionInput - A textarea with @mention autocomplete support
 * 
 * Props:
 * - value: string - The current value
 * - onChange: (value: string) => void - Called when value changes
 * - onSubmit: () => void - Called when Enter is pressed (without Shift)
 * - members: Array<{user_id, name, email, picture}> - List of mentionable users
 * - placeholder: string - Placeholder text
 * - className: string - Additional classes
 * - disabled: boolean - Whether input is disabled
 */
export function MentionInput({
  value,
  onChange,
  onSubmit,
  members = [],
  placeholder = "Add a comment... Use @ to mention someone",
  className,
  disabled = false,
}) {
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [mentionQuery, setMentionQuery] = useState("");
  const [mentionStart, setMentionStart] = useState(-1);
  const textareaRef = useRef(null);
  const suggestionsRef = useRef(null);

  // Filter members based on query
  const filterMembers = useCallback((query) => {
    if (!query) return members.slice(0, 10);
    const lowerQuery = query.toLowerCase();
    return members
      .filter(m => 
        m.name?.toLowerCase().includes(lowerQuery) ||
        m.email?.toLowerCase().includes(lowerQuery)
      )
      .slice(0, 10);
  }, [members]);

  // Handle input changes and detect @ mentions
  const handleChange = (e) => {
    const newValue = e.target.value;
    const cursorPos = e.target.selectionStart;
    
    onChange(newValue);
    
    // Find if we're in an @mention context
    const textBeforeCursor = newValue.slice(0, cursorPos);
    const lastAtIndex = textBeforeCursor.lastIndexOf('@');
    
    if (lastAtIndex !== -1) {
      // Check if there's a space between @ and cursor
      const textAfterAt = textBeforeCursor.slice(lastAtIndex + 1);
      if (!textAfterAt.includes(' ') && !textAfterAt.includes('\n')) {
        setMentionStart(lastAtIndex);
        setMentionQuery(textAfterAt);
        const filtered = filterMembers(textAfterAt);
        setSuggestions(filtered);
        setShowSuggestions(filtered.length > 0);
        setSelectedIndex(0);
        return;
      }
    }
    
    setShowSuggestions(false);
    setMentionStart(-1);
    setMentionQuery("");
  };

  // Handle keyboard navigation
  const handleKeyDown = (e) => {
    if (showSuggestions) {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex(prev => Math.min(prev + 1, suggestions.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex(prev => Math.max(prev - 1, 0));
          break;
        case 'Enter':
          if (!e.shiftKey) {
            e.preventDefault();
            if (suggestions[selectedIndex]) {
              insertMention(suggestions[selectedIndex]);
            }
          }
          break;
        case 'Escape':
          e.preventDefault();
          setShowSuggestions(false);
          break;
        case 'Tab':
          e.preventDefault();
          if (suggestions[selectedIndex]) {
            insertMention(suggestions[selectedIndex]);
          }
          break;
        default:
          break;
      }
    } else if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSubmit?.();
    }
  };

  // Insert selected mention
  const insertMention = (member) => {
    if (mentionStart === -1) return;
    
    const beforeMention = value.slice(0, mentionStart);
    const afterMention = value.slice(mentionStart + 1 + mentionQuery.length);
    const mentionText = `@${member.name} `;
    
    const newValue = beforeMention + mentionText + afterMention;
    onChange(newValue);
    
    setShowSuggestions(false);
    setMentionStart(-1);
    setMentionQuery("");
    
    // Focus back on textarea
    if (textareaRef.current) {
      const newCursorPos = beforeMention.length + mentionText.length;
      textareaRef.current.focus();
      setTimeout(() => {
        textareaRef.current.setSelectionRange(newCursorPos, newCursorPos);
      }, 0);
    }
  };

  // Scroll selected item into view
  useEffect(() => {
    if (suggestionsRef.current && showSuggestions) {
      const selectedEl = suggestionsRef.current.querySelector(`[data-index="${selectedIndex}"]`);
      selectedEl?.scrollIntoView({ block: 'nearest' });
    }
  }, [selectedIndex, showSuggestions]);

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (suggestionsRef.current && !suggestionsRef.current.contains(e.target) &&
          textareaRef.current && !textareaRef.current.contains(e.target)) {
        setShowSuggestions(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative flex-1">
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className={cn("min-h-[60px] resize-none", className)}
        disabled={disabled}
        data-testid="mention-input"
      />
      
      {showSuggestions && suggestions.length > 0 && (
        <div
          ref={suggestionsRef}
          className="absolute bottom-full left-0 mb-1 w-64 bg-popover border border-border rounded-md shadow-lg z-50 overflow-hidden"
          data-testid="mention-suggestions"
        >
          <div className="p-1 text-xs text-muted-foreground border-b px-2 py-1">
            Mention someone
          </div>
          <div className="max-h-48 overflow-y-auto">
            {suggestions.map((member, index) => (
              <div
                key={member.user_id}
                data-index={index}
                className={cn(
                  "flex items-center gap-2 px-2 py-1.5 cursor-pointer transition-colors",
                  index === selectedIndex ? "bg-accent" : "hover:bg-accent/50"
                )}
                onClick={() => insertMention(member)}
                data-testid={`mention-option-${member.user_id}`}
              >
                <Avatar className="h-6 w-6">
                  <AvatarImage src={member.picture} />
                  <AvatarFallback className="text-xs">
                    {member.name?.charAt(0)?.toUpperCase() || '?'}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{member.name}</div>
                  <div className="text-xs text-muted-foreground truncate">{member.email}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * RenderMentions - Renders text with highlighted @mentions
 */
export function RenderMentions({ text, members = [] }) {
  if (!text) return null;
  
  // Create a map of names to user info
  const memberMap = new Map(members.map(m => [m.name?.toLowerCase(), m]));
  
  // Split text by @mentions
  const parts = text.split(/(@\w+(?:\s+\w+)?)/g);
  
  return (
    <span>
      {parts.map((part, index) => {
        if (part.startsWith('@')) {
          const mentionName = part.slice(1).toLowerCase();
          const member = memberMap.get(mentionName);
          
          if (member) {
            return (
              <span
                key={index}
                className="inline-flex items-center gap-1 px-1 py-0.5 bg-primary/10 text-primary rounded text-sm font-medium"
                title={member.email}
              >
                {part}
              </span>
            );
          }
          // Unknown mention - still highlight but differently
          return (
            <span
              key={index}
              className="text-primary font-medium"
            >
              {part}
            </span>
          );
        }
        return <span key={index}>{part}</span>;
      })}
    </span>
  );
}

export default MentionInput;
