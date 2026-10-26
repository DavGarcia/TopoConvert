const EN_TO_FA_MAP: Record<string, string> = {
  "0": "۰",
  "1": "۱",
  "2": "۲",
  "3": "۳",
  "4": "۴",
  "5": "۵",
  "6": "۶",
  "7": "۷",
  "8": "۸",
  "9": "۹"
};

export function toPersianDigits(input: string | number, enabled = true): string {
  const str = String(input);
  if (!enabled) {
    return str;
  }
  return str.replace(/[0-9]/g, (d) => EN_TO_FA_MAP[d] ?? d);
}

export function formatNum(
  value: number | undefined | null,
  decimals = 2,
  persianDigits = true
): string {
  if (value === undefined || value === null || Number.isNaN(value)) {
    return toPersianDigits("0", persianDigits);
  }
  const formatted = Number(value).toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
  return toPersianDigits(formatted, persianDigits);
}

export function formatInt(
  value: number | undefined | null,
  persianDigits = true
): string {
  if (value === undefined || value === null || Number.isNaN(value)) {
    return toPersianDigits("0", persianDigits);
  }
  const formatted = Math.round(Number(value)).toLocaleString("en-US");
  return toPersianDigits(formatted, persianDigits);
}
