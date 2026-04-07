import { useState } from 'react';
import { Plus, X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ListEditorProps {
  items: string[];
  onChange: (items: string[]) => void;
  label: string;
  placeholder?: string;
  description?: string;
  className?: string;
}

export function ListEditor({ items, onChange, label, placeholder = 'Add item...', description, className }: ListEditorProps) {
  const [inputValue, setInputValue] = useState('');

  const addItem = () => {
    const trimmed = inputValue.trim();
    if (!trimmed) return;
    if (items.some((item) => item.toLowerCase() === trimmed.toLowerCase())) return;
    onChange([...items, trimmed]);
    setInputValue('');
  };

  const removeItem = (index: number) => {
    onChange(items.filter((_, i) => i !== index));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addItem();
    }
  };

  const isDuplicate = inputValue.trim() !== '' && items.some((item) => item.toLowerCase() === inputValue.trim().toLowerCase());

  return (
    <div className={cn('space-y-2', className)}>
      <label className="text-sm font-semibold text-slate-700">{label}</label>
      {description && <p className="text-xs text-slate-500">{description}</p>}
      <div className="flex gap-2">
        <input
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className={cn(
            'flex-1 px-3 py-1.5 border rounded-lg text-sm outline-none transition-all',
            isDuplicate
              ? 'border-amber-300 focus:ring-2 focus:ring-amber-500/10'
              : 'border-slate-200 focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500'
          )}
        />
        <button
          type="button"
          onClick={addItem}
          disabled={!inputValue.trim() || isDuplicate}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 disabled:bg-slate-50 disabled:text-slate-300 text-slate-600 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          Add
        </button>
      </div>
      {isDuplicate && <p className="text-xs text-amber-600">This item already exists.</p>}
      {items.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-1">
          {items.map((item, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-indigo-50 text-indigo-700 rounded-md text-xs font-medium border border-indigo-100"
            >
              {item}
              <button
                type="button"
                onClick={() => removeItem(i)}
                className="hover:text-indigo-900 hover:bg-indigo-100 rounded-full p-0.5 transition-colors"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
