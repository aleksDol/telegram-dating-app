import { Link } from 'react-router-dom'

const LOGO_SRC = '/images/Spon.png'

type LogoProps = {
  size?: 'sm' | 'md' | 'lg'
  showText?: boolean
  link?: boolean
}

const sizes = {
  sm: { circle: 36, text: '1rem' },
  md: { circle: 44, text: '1.2rem' },
  lg: { circle: 56, text: '1.5rem' },
}

export default function Logo({ size = 'md', showText = true, link = false }: LogoProps) {
  const { circle: circleSize, text: textSize } = sizes[size]
  const content = (
    <div className="app-logo" style={{ ['--logo-circle-size' as string]: `${circleSize}px`, ['--logo-text-size' as string]: textSize }}>
      <div className="app-logo-circle">
        <img src={LOGO_SRC} alt="" className="app-logo-img" />
      </div>
      {showText && <span className="app-logo-text">Знакомься по-новому</span>}
    </div>
  )
  if (link) {
    return <Link to="/" className="app-logo-link">{content}</Link>
  }
  return content
}
