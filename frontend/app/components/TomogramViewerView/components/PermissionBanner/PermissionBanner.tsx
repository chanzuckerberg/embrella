import { Callout } from '@czi-sds/components';

interface PermissionBannerProps {
  ownerName: string;
}

export const PermissionBanner = ({ ownerName }: PermissionBannerProps) => {
  const body = (
    <span className="flex flex-col justify-center items-center">
      You don&apos;t have permission to submit annotations for this review. This review is owned by {ownerName}.
    </span>
  );
  return (
    <div className="w-full px-6 py-3">
      <Callout intent="notice" sdsStyle="persistent" variant="filled" body={body} />
    </div>
  );
};
