import { AutocompleteOptionBasic, DropdownMenu, InputDropdown } from '@czi-sds/components';
import { SyntheticEvent, useRef, useState } from 'react';

interface DropdownSelectProps<T> {
  value?: T;
  options: T[];

  topLabel: string;
  topLabelClass?: string;
  disabled?: boolean;

  onChange: (option?: T) => void;
}

export const DropdownSelect = <T extends AutocompleteOptionBasic>({
  value,
  options,
  topLabel,
  topLabelClass,
  disabled = false,
  onChange,
}: DropdownSelectProps<T>) => {
  const inputRef = useRef<HTMLElement | null>(null);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  const handleDropdownClick = (event: React.MouseEvent<HTMLElement>) => {
    inputRef.current = event.currentTarget;
    setIsDropdownOpen((prev) => !prev);
  };
  const handleOptionChange = (_event: SyntheticEvent, option: T) => {
    onChange(option);
    setIsDropdownOpen(false);
  };
  const handleClickAway = () => {
    setIsDropdownOpen(false);
  };

  return (
    <>
      <div className={`font-semibold ${topLabelClass}`}>{topLabel}</div>
      <InputDropdown
        label="Select"
        value={value?.name}
        onClick={handleDropdownClick}
        disabled={disabled}
        sdsType="value"
        sdsStage="default"
      />
      <DropdownMenu
        search
        options={options}
        open={isDropdownOpen}
        value={value}
        // @ts-expect-error -- SDS type is not specific enough.
        onChange={handleOptionChange}
        onClickAway={handleClickAway}
        anchorEl={inputRef.current}
        width={inputRef.current?.clientWidth}
      />
    </>
  );
};
