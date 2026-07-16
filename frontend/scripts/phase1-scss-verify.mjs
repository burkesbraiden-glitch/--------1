import { compileString } from 'sass'

const result = compileString(
  `@use "variables" as *;

.scss-verify {
  color: $tl-primary;
  background: $tl-bg;
  border-radius: $tl-radius-md;
}`,
  {
    loadPaths: ['src/styles'],
    style: 'expanded',
  },
)

const css = result.css

if (!css.includes('#f26a21') || !css.includes('#f8efd9') || !css.includes('24rpx')) {
  throw new Error('SCSS variables did not compile into expected CSS values')
}

console.log('scss variables compile check passed')
