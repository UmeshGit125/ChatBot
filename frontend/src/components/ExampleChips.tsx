'use client';

const EXAMPLE_QUESTIONS = [
  'How many students are enrolled?',
  'Show top 5 students in Mathematics',
  'What is the average attendance?',
  'List students with attendance below 75%',
];

interface ExampleChipsProps {
  onSelect: (question: string) => void;
}

export function ExampleChips({ onSelect }: ExampleChipsProps) {
  return (
    <div className="flex flex-wrap justify-center gap-2 mt-4">
      {EXAMPLE_QUESTIONS.map((q) => (
        <button
          key={q}
          onClick={() => onSelect(q)}
          className="px-3 py-2 text-sm rounded-xl border border-border-light dark:border-border-dark hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-gray-600 dark:text-gray-300"
        >
          {q}
        </button>
      ))}
    </div>
  );
}
