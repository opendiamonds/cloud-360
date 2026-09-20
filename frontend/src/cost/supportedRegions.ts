export type CloudId = 'aws' | 'gcp' | 'azure';

export type SupportedRegion = {
  value: string;
  label: string;
  cloud: CloudId;
};

export const SUPPORTED_REGIONS: SupportedRegion[] = [
  { value: 'us-east-1', label: 'us-east-1', cloud: 'aws' },
  { value: 'us-west-2', label: 'us-west-2', cloud: 'aws' },
  { value: 'eu-west-1', label: 'eu-west-1', cloud: 'aws' },
  { value: 'ap-northeast-1', label: 'ap-northeast-1 (Tokyo)', cloud: 'aws' },
  { value: 'ap-southeast-1', label: 'ap-southeast-1 (Singapore)', cloud: 'aws' },
  { value: 'ap-east-2', label: 'ap-east-2 (Taipei)', cloud: 'aws' },
  { value: 'us-central1', label: 'us-central1', cloud: 'gcp' },
  { value: 'us-east1', label: 'us-east1', cloud: 'gcp' },
  { value: 'europe-west1', label: 'europe-west1', cloud: 'gcp' },
  { value: 'asia-east1', label: 'asia-east1 (Taiwan / Changhua)', cloud: 'gcp' },
  { value: 'asia-northeast1', label: 'asia-northeast1 (Tokyo)', cloud: 'gcp' },
  { value: 'asia-southeast1', label: 'asia-southeast1 (Singapore)', cloud: 'gcp' },
  { value: 'eastus', label: 'eastus', cloud: 'azure' },
  { value: 'westus2', label: 'westus2', cloud: 'azure' },
  { value: 'westeurope', label: 'westeurope', cloud: 'azure' },
  { value: 'japaneast', label: 'japaneast (Tokyo)', cloud: 'azure' },
  { value: 'southeastasia', label: 'southeastasia (Singapore)', cloud: 'azure' },
  { value: 'eastasia', label: 'eastasia (Hong Kong)', cloud: 'azure' },
];

const CLOUD_LABEL: Record<CloudId, string> = {
  aws: 'AWS',
  gcp: 'GCP',
  azure: 'Azure',
};

export function regionsForCloud(cloud: string | null | undefined): SupportedRegion[] {
  if (cloud === 'aws' || cloud === 'gcp' || cloud === 'azure') {
    return SUPPORTED_REGIONS.filter((r) => r.cloud === cloud);
  }
  return SUPPORTED_REGIONS;
}

export function cloudDisplayName(cloud: string | null | undefined): string {
  if (cloud === 'aws' || cloud === 'gcp' || cloud === 'azure') {
    return CLOUD_LABEL[cloud];
  }
  return '未知';
}
