import React, { useState } from 'react';

interface ObjectLabelsSelectorProps {
  availableObjects: string[];
  selectedObjects: string[];
  setSelectedObjects: (selected: string[]) => void;
}

export const ObjectLabelsSelector: React.FC<ObjectLabelsSelectorProps> = ({
  availableObjects,
  selectedObjects,
  setSelectedObjects,
}) => {
  const [search, setSearch] = useState('');

  const filteredObjects = availableObjects.filter((obj) => obj.toLowerCase().includes(search.toLowerCase()));

  const handleToggle = (obj: string) => {
    if (selectedObjects.includes(obj)) {
      setSelectedObjects(selectedObjects.filter((o) => o !== obj));
    } else {
      setSelectedObjects([...selectedObjects, obj]);
    }
  };

  return (
    <div className="mt-4 flex flex-col gap-2">
      <div className="font-bold">
        Add Global Object Labels <span className="font-normal">(Optional)</span>
      </div>
      <div className="text-sm mb-2">Select all that appear in this tomogram.</div>
      <input
        type="text"
        placeholder="Search"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="border border-gray-300 px-2 py-1 mb-2 w-full"
      />
      <div className="max-h-45 overflow-y-auto rounded p-2">
        {filteredObjects.map((obj) => (
          <label key={obj} className="flex items-center mb-1 cursor-pointer">
            <input
              type="checkbox"
              checked={selectedObjects.map((o) => o.toLowerCase()).includes(obj.toLowerCase())}
              onChange={() => handleToggle(obj)}
              className="!mr-3"
            />
            {obj}
          </label>
        ))}
        {filteredObjects.length === 0 && <div className="text-gray-400 italic">No matches</div>}
      </div>
    </div>
  );
};
