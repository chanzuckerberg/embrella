import { UserContext } from '@app/common/context/UserProvider';
import { EntityLinkField } from '@app/common/types/entity';
import { Button, DropdownMenu, Icon } from '@czi-sds/components';
import Link from 'next/link';
import { useContext, useRef, useState } from 'react';
import { API, DJANGO_URL } from '@app/common/constants/api';

export interface ReviewActionButtonProps {
  reviewId: string;
  reviewStatus: string;
  _reviewer: EntityLinkField;
  reviewedCount?: number;
  totalCount?: number;
}

export const ReviewActionButton = ({
  reviewId,
  reviewStatus,
  _reviewer,
  reviewedCount = 0,
  totalCount = 0,
}: ReviewActionButtonProps) => {
  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const currentUser = useContext(UserContext);

  if (currentUser === undefined) {
    return <div>Loading...</div>;
  }

  // Check if all tomograms have been reviewed
  const allTomogramsReviewed = reviewedCount > 0 && reviewedCount === totalCount;

  const reviewUrl = `/reviews/${reviewId}`;

  // Download handler for export
  const handleExportResults = async () => {
    try {
      // Remove dashes from review ID
      const reviewIdNoDashes = reviewId.replace(/-/g, '');
      const url = `${DJANGO_URL}${API.REVIEW_EXPORT.replace(':reviewId', reviewIdNoDashes)}`;
      const response = await fetch(url);
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.details || errorData.error || 'Failed to export review results');
      }
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `review_${reviewIdNoDashes}_export.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (error: unknown) {
      if (error instanceof Error) {
        alert(error.message);
      } else {
        alert('Failed to download review results.');
      }
    }
  };

  // Show "View Results" with download option when all tomograms are reviewed
  if (allTomogramsReviewed) {
    return (
      <div className="flex justify-end">
        <Button
          sdsType="secondary"
          sdsStyle="square"
          size="small"
          className="w-[125px]"
          endIcon={<Icon sdsIcon="ChevronDown" sdsSize="xs" />}
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
                </Link>
              ),
            },
            {
              name: 'download',
              component: (
                <div className="flex flex-col" onClick={handleExportResults} style={{ cursor: 'pointer' }}>
                  <div>Export Results (.json)</div>
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
      </div>
    );
  } else {
    // Show "Start Review" or "Resume Review" when not all tomograms are reviewed
    return (
      <div className="flex justify-end">
        <Link href={reviewUrl}>
          <Button sdsType="secondary" sdsStyle="square" size="small" className="w-[125px]">
            {reviewStatus === 'Not Started' ? 'Start Review' : 'Resume Review'}
          </Button>
        </Link>
      </div>
    );
  }
};
