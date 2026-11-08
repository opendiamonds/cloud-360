import type { IacStep } from './iacTypes';

export const IAC_GROUP_LABEL = '基礎建設';

export const IAC_NAV_ITEMS: {
  step: IacStep;
  storyId: 'D1' | 'D2' | 'D3';
  path: string;
  label: string;
}[] = [
  { step: 'generate', storyId: 'D1', path: '/iac/generate', label: 'Terraform 產出' },
  { step: 'scan', storyId: 'D2', path: '/iac/scan', label: 'IaC 安全掃描' },
  { step: 'secrets', storyId: 'D3', path: '/iac/secrets', label: 'Secret／敏感值' },
];

export function iacNavItem(step: string | undefined) {
  return IAC_NAV_ITEMS.find((item) => item.step === step);
}
