def get_icon_svg():
    return """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
      <!-- Background circle -->
      <circle cx="50" cy="50" r="45" fill="#1E88E5" />
      
      <!-- Dollar sign -->
      <text x="50" y="65" font-family="Arial" font-size="50" font-weight="bold" fill="white" text-anchor="middle">$</text>
      
      <!-- Surrounding arrows to symbolize arbitrage -->
      <g fill="white" stroke="white" stroke-width="2">
        <!-- Top arrow -->
        <path d="M50,10 L60,25 L40,25 Z" />
        
        <!-- Right arrow -->
        <path d="M90,50 L75,60 L75,40 Z" />
        
        <!-- Bottom arrow -->
        <path d="M50,90 L40,75 L60,75 Z" />
        
        <!-- Left arrow -->
        <path d="M10,50 L25,40 L25,60 Z" />
      </g>
    </svg>
    """