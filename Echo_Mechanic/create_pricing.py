import os

# Read dashboard.html
try:
    with open('dashboard.html', 'r', encoding='utf-8') as f:
        content = f.read()
except FileNotFoundError:
    print("Error: dashboard.html not found")
    exit(1)

if '</aside>' not in content:
    print("Error: </aside> tag not found in dashboard.html")
    exit(1)

# Split at the end of the sidebar
parts = content.split('</aside>')
# Take everything up to and including the closing aside tag
# This includes the head, body start, background div, wrapper div start, and the sidebar itself
pre_sidebar = parts[0] + '</aside>'

# Define the new pricing content
# We inject the main content area with the pricing grid
# We attempt to match the classes from dashboard.html (assuming standard structure) 
# or use generic tailwind classes that fit the "dark theme" requirement.
pricing_html = """
        <!-- Main Content -->
        <main class="flex-1 h-full overflow-y-auto bg-background-dark relative z-10">
            <div class="p-6 md:p-12 max-w-7xl mx-auto">
                <h1 class="text-3xl font-bold text-white mb-10">Escolha o seu Plano</h1>
                
                <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
                    <!-- Grátis Card -->
                    <div class="bg-surface-dark border border-surface-lighter rounded-2xl p-8 flex flex-col hover:border-surface-lighter/80 transition-colors">
                        <div class="mb-6">
                            <h2 class="text-xl font-semibold text-white">Grátis</h2>
                            <div class="mt-4 flex items-baseline">
                                <span class="text-4xl font-bold text-white">0€</span>
                                <span class="ml-1 text-text-dim">/mês</span>
                            </div>
                        </div>
                        <ul class="space-y-4 mb-8 flex-1">
                            <li class="flex items-start gap-3">
                                <span class="material-symbols-outlined text-green-500 text-xl shrink-0">check</span>
                                <span class="text-text-dim text-sm">Funcionalidades essenciais</span>
                            </li>
                            <li class="flex items-start gap-3">
                                <span class="material-symbols-outlined text-green-500 text-xl shrink-0">check</span>
                                <span class="text-text-dim text-sm">Acesso limitado</span>
                            </li>
                        </ul>
                        <button class="w-full py-3 px-4 bg-surface-lighter hover:bg-[#2A3B44] text-white font-medium rounded-xl transition-all active:scale-[0.98]">
                            Atual
                        </button>
                    </div>

                    <!-- Profissional Card -->
                    <div class="bg-surface-dark border border-primary/40 rounded-2xl p-8 flex flex-col relative overflow-hidden shadow-lg shadow-primary/5">
                        <div class="absolute top-0 right-0 bg-primary text-black text-xs font-bold px-3 py-1.5 rounded-bl-xl">MAIS POPULAR</div>
                        
                        <div class="mb-6">
                            <h2 class="text-xl font-semibold text-primary">Profissional</h2>
                            <div class="mt-4 flex items-baseline">
                                <span class="text-4xl font-bold text-white">29,90€</span>
                                <span class="ml-1 text-text-dim">/mês</span>
                            </div>
                        </div>
                        <ul class="space-y-4 mb-8 flex-1">
                            <li class="flex items-start gap-3">
                                <span class="material-symbols-outlined text-green-500 text-xl shrink-0">check</span>
                                <span class="text-text-dim text-sm">Todas as funcionalidades Grátis</span>
                            </li>
                            <li class="flex items-start gap-3">
                                <span class="material-symbols-outlined text-green-500 text-xl shrink-0">check</span>
                                <span class="text-text-dim text-sm">Suporte priorizado</span>
                            </li>
                            <li class="flex items-start gap-3">
                                <span class="material-symbols-outlined text-green-500 text-xl shrink-0">check</span>
                                <span class="text-text-dim text-sm">Análises avançadas</span>
                            </li>
                        </ul>
                        <a href="checkout.html" class="w-full py-3 px-4 bg-primary hover:bg-primary-hover text-black font-semibold rounded-xl transition-all text-center block active:scale-[0.98]">
                            Subscrever
                        </a>
                    </div>

                    <!-- Anual Card -->
                    <div class="bg-surface-dark border border-surface-lighter rounded-2xl p-8 flex flex-col hover:border-surface-lighter/80 transition-colors">
                        <div class="mb-6">
                            <h2 class="text-xl font-semibold text-white">Anual</h2>
                            <div class="mt-4 flex items-baseline">
                                <span class="text-4xl font-bold text-white">24,90€</span>
                                <span class="ml-1 text-text-dim">/mês</span>
                            </div>
                            <div class="mt-2 inline-block px-2.5 py-0.5 rounded-full bg-green-500/10 text-green-400 text-xs font-medium border border-green-500/20">
                                Poupe 17% ao ano
                            </div>
                        </div>
                        <ul class="space-y-4 mb-8 flex-1">
                            <li class="flex items-start gap-3">
                                <span class="material-symbols-outlined text-green-500 text-xl shrink-0">check</span>
                                <span class="text-text-dim text-sm">Tudo do Profissional</span>
                            </li>
                            <li class="flex items-start gap-3">
                                <span class="material-symbols-outlined text-green-500 text-xl shrink-0">check</span>
                                <span class="text-text-dim text-sm">Faturação simplificada</span>
                            </li>
                        </ul>
                        <button class="w-full py-3 px-4 bg-surface-lighter hover:bg-[#2A3B44] text-white font-medium rounded-xl transition-all active:scale-[0.98]">
                            Ver Anual
                        </button>
                    </div>
                </div>
            </div>
        </main>
    </div>
</body>
</html>
"""

# Combine parts
full_content = pre_sidebar + pricing_html

# Write pricing.html
try:
    with open('pricing.html', 'w', encoding='utf-8') as f:
        f.write(full_content)
    print("Success: pricing.html created")
except Exception as e:
    print(f"Error writing file: {e}")
