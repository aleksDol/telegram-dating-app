import { Link } from 'react-router-dom'

type LogoProps = {
  size?: 'sm' | 'md' | 'lg'
  showText?: boolean
  link?: boolean
}

const sizes = {
  sm: { icon: 28, text: '1.25rem' },
  md: { icon: 40, text: '1.6rem' },
  lg: { icon: 56, text: '2.25rem' },
}

export default function Logo({ size = 'md', showText = true, link = false }: LogoProps) {
  const { icon: iconSize, text: textSize } = sizes[size]
  const content = (
    <div className="app-logo" style={{ ['--logo-icon-size' as string]: `${iconSize}px`, ['--logo-text-size' as string]: textSize }}>
      <span className="app-logo-icon" aria-hidden>💫</span>
      {showText && <span className="app-logo-text">Встречи</span>}
    </div>
  )
  if (link) {
    return <Link to="/" className="app-logo-link">{content}</Link>
  }
  return content
}
