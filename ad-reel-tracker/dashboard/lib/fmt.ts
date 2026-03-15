/**
 * 비용 포맷: 적어도 유효숫자 2개가 보이도록 소수점 자릿수 자동 결정
 *   >= 10   → 정수 (1,429원)
 *   1~9.9   → 소수 1자리 (6.1원)
 *   0.1~0.9 → 소수 2자리 (0.14원)
 *   0.01~   → 소수 3자리, 이하 동일 패턴
 */
export function fmtCost(v: number): string {
  if (v >= 10) return Math.round(v).toLocaleString('ko-KR') + '원';
  if (v >= 1)  return v.toFixed(1) + '원';
  if (v >= 0.1) return v.toFixed(2) + '원';
  // 0.1 미만: 첫 번째 유효숫자 위치 찾아서 +2자리
  const decimals = Math.floor(-Math.log10(v)) + 2;
  return v.toFixed(Math.min(decimals, 10)) + '원';
}
