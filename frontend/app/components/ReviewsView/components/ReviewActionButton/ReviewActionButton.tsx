import { UserContext } from '@app/common/context/UserProvider';
import { EntityLinkField } from '@app/common/types/entity';
import { Button, DropdownMenu, Icon } from '@czi-sds/components';
import Link from 'next/link';
import { useContext, useRef, useState } from 'react';

export interface ReviewActionButtonProps {
  reviewId: number;
  reviewStatus: string;
  reviewer: EntityLinkField;
}

export const ReviewActionButton = ({ reviewId, reviewStatus, reviewer }: ReviewActionButtonProps) => {
  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const currentUser = useContext(UserContext);

  if (currentUser === undefined) {
    return null;
  }

  const userCanReview =
    reviewStatus === 'not_started' || (reviewStatus === 'in_progress' && currentUser.id === reviewer.id);
  const reviewUrl = `/reviews/${reviewId}`;

  if (userCanReview) {
    return (
      <Link href={reviewUrl}>
        <Button sdsType="secondary" sdsStyle="square" size="small" className="w-[125px]">
          {reviewStatus === 'not_started' ? 'Start Review' : 'Resume Review'}
        </Button>
      </Link>
    );
  } else {
    return (
      <>
        <Button
          sdsType="secondary"
          sdsStyle="square"
          size="small"
          className="w-[125px]"
          endIcon={<Icon sdsIcon="ChevronDown" sdsSize="xs" sdsType="button" />}
          onClick={() => {
            setIsDropdownOpen((prev) => !prev);
          }}
          ref={buttonRef}
        >
          View Results
        </Button>
        <DropdownMenu
          label="View Results"
          options={[
            {
              name: 'view',
              component: (
                <Link href={reviewUrl} className="flex flex-col">
                  <div>Open Results Viewer</div>
                  {reviewStatus === 'in_progress' && (
                    <div className="text-[#c6c6c6] text-[12px]">Results may be incomplete</div>
                  )}
                </Link>
              ),
            },
            {
              name: 'download',
              component: (
                <div className="flex flex-col">
                  <div>Export Results (.json)</div>
                  {reviewStatus === 'in_progress' && (
                    <div className="text-[#c6c6c6] text-[12px]">Results may be incomplete</div>
                  )}
                </div>
              ),
            },
          ]}
          open={isDropdownOpen}
          onClickAway={() => {
            setIsDropdownOpen(false);
          }}
          anchorEl={buttonRef.current}
          PopperBaseProps={{
            className: 'relative right-10 z-50 rounded-sds-m !w-[240px]',
            popperOptions: {
              modifiers: [
                {
                  name: 'offset',
                  options: {
                    offset: [0, 1],
                  },
                },
              ],
              placement: 'bottom-end',
            },
          }}
        />
      </>
    );
  }
};
