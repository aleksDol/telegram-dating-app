import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'
import bgImage from './img/bg.jpeg'

// Фон всех страниц на body — ни один блок не перекроет
document.body.style.backgroundImage = `url(${bgImage})`
document.body.classList.add('app-bg-body')

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
