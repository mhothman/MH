import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { globalSearch } from '../api/search';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { LoadingSpinner } from './ui/loading-spinner';
import { Search, FolderKanban, CheckSquare, MessageSquare, X } from 'lucide-react';
import { useDebounce } from '../hooks/useDebounce';

export const GlobalSearch = () => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);
  const inputRef = useRef(null);
  
  const debouncedQuery = useDebounce(query, 300);

  const performSearch = useCallback(async (searchQuery) => {
    if (searchQuery.length < 2) {
      setResults([]);
      return;
    }

    setLoading(true);
    try {
      const data = await globalSearch(searchQuery);
      setResults(data.results || []);
    } catch (error) {
      console.error('Search failed:', error);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    performSearch(debouncedQuery);
  }, [debouncedQuery, performSearch]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Keyboard shortcut (Cmd/Ctrl + K)
  useEffect(() => {
    const handleKeyDown = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
        event.preventDefault();
        inputRef.current?.focus();
        setIsOpen(true);
      }
      if (event.key === 'Escape') {
        setIsOpen(false);
        inputRef.current?.blur();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleResultClick = (result) => {
    setIsOpen(false);
    setQuery('');
    
    if (result.type === 'project') {
      navigate(`/projects/${result.id}`);
    } else if (result.type === 'task') {
      navigate(`/projects/${result.project_id}?task=${result.id}`);
    } else if (result.type === 'comment' && result.project_id) {
      navigate(`/projects/${result.project_id}`);
    }
  };

  const getIcon = (type) => {
    switch (type) {
      case 'project':
        return <FolderKanban className="w-4 h-4 text-blue-500" />;
      case 'task':
        return <CheckSquare className="w-4 h-4 text-green-500" />;
      case 'comment':
        return <MessageSquare className="w-4 h-4 text-purple-500" />;
      default:
        return null;
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      todo: 'bg-slate-500',
      in_progress: 'bg-blue-500',
      review: 'bg-purple-500',
      done: 'bg-green-500',
      active: 'bg-green-500',
      planned: 'bg-slate-500',
    };
    return colors[status] || 'bg-slate-500';
  };

  return (
    <div className="relative" ref={containerRef} data-testid="global-search">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          ref={inputRef}
          type="text"
          placeholder="Search... (⌘K)"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          className="pl-9 pr-9 w-64"
          data-testid="search-input"
        />
        {query && (
          <button
            onClick={() => {
              setQuery('');
              setResults([]);
            }}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {isOpen && query.length >= 2 && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-card border border-border rounded-lg shadow-lg z-50 max-h-[400px] overflow-y-auto" data-testid="search-results">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <LoadingSpinner size="md" />
            </div>
          ) : results.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground">
              No results found for "{query}"
            </div>
          ) : (
            <div className="py-2">
              {results.map((result, index) => (
                <button
                  key={`${result.type}-${result.id}-${index}`}
                  onClick={() => handleResultClick(result)}
                  className="w-full px-4 py-3 hover:bg-accent flex items-start gap-3 text-left transition-colors"
                  data-testid={`search-result-${result.type}-${result.id}`}
                >
                  <div className="flex-shrink-0 mt-0.5">
                    {getIcon(result.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium truncate">{result.title}</span>
                      {result.status && (
                        <span className={`w-2 h-2 rounded-full ${getStatusColor(result.status)}`} />
                      )}
                    </div>
                    {result.description && (
                      <p className="text-sm text-muted-foreground truncate mt-0.5">
                        {result.description.replace(/<[^>]*>/g, '').slice(0, 100)}
                      </p>
                    )}
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="outline" className="text-xs">
                        {result.type}
                      </Badge>
                      {result.project_name && result.type !== 'project' && (
                        <span className="text-xs text-muted-foreground">
                          in {result.project_name}
                        </span>
                      )}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default GlobalSearch;
