class CustomRichTextEditor {
    constructor(selector, options = {}) {
        this.editor = document.querySelector(selector);
        if (!this.editor) return;
        
        // Create toolbar
        this.createToolbar();
        
        // Setup editor
        this.setupEditor();
        
        // Initialize with options
        this.init(options);

        // Setup LaTeX rendering
        this.setupLatexRendering();
    }

    createToolbar() {
        const toolbar = document.createElement('div');
        toolbar.className = 'editor-toolbar btn-group mb-2';
        
        // Add buttons
        const buttons = [
            { cmd: 'bold', icon: 'fa-bold', title: 'عريض' },
            { cmd: 'italic', icon: 'fa-italic', title: 'مائل' },
            { cmd: 'underline', icon: 'fa-underline', title: 'تحته خط' },
            { cmd: 'insertUnorderedList', icon: 'fa-list-ul', title: 'قائمة نقطية' },
            { cmd: 'insertOrderedList', icon: 'fa-list-ol', title: 'قائمة رقمية' },
            { cmd: 'justifyRight', icon: 'fa-align-right', title: 'محاذاة لليمين' },
            { cmd: 'justifyCenter', icon: 'fa-align-center', title: 'توسيط' },
            { cmd: 'justifyLeft', icon: 'fa-align-left', title: 'محاذاة لليسار' },
            { cmd: 'insertLatex', icon: 'fa-square-root-variable', title: 'معادلة رياضية', custom: true },
            { cmd: 'insertChemistry', icon: 'fa-flask', title: 'معادلة كيميائية', custom: true },
            { cmd: 'subscript', icon: 'fa-subscript', title: 'نص منخفض' },
            { cmd: 'superscript', icon: 'fa-superscript', title: 'نص مرتفع' }
        ];

        buttons.forEach(btn => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'btn btn-outline-secondary btn-sm';
            button.title = btn.title;
            button.innerHTML = `<i class="fas ${btn.icon}"></i>`;
            button.onclick = (e) => {
                e.preventDefault();
                if (btn.custom) {
                    this.handleCustomCommand(btn.cmd);
                } else {
                    document.execCommand(btn.cmd, false, null);
                }
                this.editor.focus();
            };
            toolbar.appendChild(button);
        });

        // Insert toolbar before editor
        this.editor.parentNode.insertBefore(toolbar, this.editor);
    }

    handleCustomCommand(cmd) {
        switch (cmd) {
            case 'insertLatex':
                this.insertLatexDialog();
                break;
            case 'insertChemistry':
                this.insertChemistryDialog();
                break;
        }
    }

    insertLatexDialog() {
        const latex = prompt('أدخل معادلة LaTeX:', '');
        if (latex) {
            const displayMode = confirm('هل تريد عرض المعادلة في سطر منفصل؟');
            const delimiter = displayMode ? '$$' : '$';
            const content = `${delimiter}${latex}${delimiter}`;
            
            // Insert at cursor position
            const selection = window.getSelection();
            const range = selection.getRangeAt(0);
            const textNode = document.createTextNode(content);
            range.insertNode(textNode);
            
            // Move cursor after equation
            range.setStartAfter(textNode);
            range.setEndAfter(textNode);
            selection.removeAllRanges();
            selection.addRange(range);
            
            // Re-render math in editor
            renderMathInElement(this.editor, {
                delimiters: [
                    {left: "$$", right: "$$", display: true},
                    {left: "$", right: "$", display: false}
                ],
                throwOnError: false
            });
        }
    }

    insertChemistryDialog() {
        const formula = prompt('أدخل معادلة كيميائية:', '');
        if (formula) {
            // Insert the chemistry formula with delimiters
            const displayMode = confirm('هل تريد عرض المعادلة في سطر منفصل؟');
            const content = displayMode ? 
                `\\[\\ce{${formula}}\\]` : 
                `\\(\\ce{${formula}}\\)`;
            
            // Insert at cursor position
            const selection = window.getSelection();
            const range = selection.getRangeAt(0);
            const textNode = document.createTextNode(content);
            range.insertNode(textNode);
            
            // Move cursor after equation
            range.setStartAfter(textNode);
            range.setEndAfter(textNode);
            selection.removeAllRanges();
            selection.addRange(range);
            
            // Re-render math in editor
            renderMathInElement(this.editor, {
                delimiters: [
                    {left: "\\[", right: "\\]", display: true},
                    {left: "\\(", right: "\\)", display: false}
                ],
                throwOnError: false,
                trust: true
            });
        }
    }

    setupLatexRendering() {
        // Auto-render LaTeX when content changes
        this.editorDiv.addEventListener('input', () => {
            this.renderLatexEquations();
        });
    }

    renderLatexEquations() {
        const equations = this.editorDiv.querySelectorAll('.latex-equation, .chemistry-equation');
        equations.forEach(eq => {
            if (!eq.hasAttribute('data-rendered')) {
                try {
                    katex.render(eq.textContent, eq, {
                        throwOnError: false,
                        displayMode: true
                    });
                    eq.setAttribute('data-rendered', 'true');
                } catch (e) {
                    console.error('Render Error:', e);
                }
            }
        });
    }

    setupEditor() {
        // Make the textarea into a contenteditable div
        const editorDiv = document.createElement('div');
        editorDiv.className = 'custom-editor form-control';
        editorDiv.contentEditable = true;
        editorDiv.style.minHeight = '200px';
        editorDiv.style.maxHeight = '500px';
        editorDiv.style.overflow = 'auto';
        editorDiv.style.direction = 'rtl';
        editorDiv.style.textAlign = 'right';
        
        // Replace textarea with editable div
        this.editor.parentNode.replaceChild(editorDiv, this.editor);
        this.editorDiv = editorDiv;

        // Setup equation editing
        this.setupEquationEditing();
        
        // Create hidden input to store HTML content
        this.hiddenInput = document.createElement('input');
        this.hiddenInput.type = 'hidden';
        this.hiddenInput.name = this.editor.name;
        this.hiddenInput.id = this.editor.id;
        editorDiv.parentNode.appendChild(this.hiddenInput);
        
        // Update hidden input when content changes
        editorDiv.addEventListener('input', () => {
            this.hiddenInput.value = editorDiv.innerHTML;
        });
    }

    setupEquationEditing() {
        // Handle input in equation source
        this.editorDiv.addEventListener('input', (e) => {
            const source = e.target.closest('.equation-source');
            if (source) {
                const wrapper = source.parentElement;
                this.renderEquation(wrapper);
            }
        });

        // Handle focus/blur for equation display
        this.editorDiv.addEventListener('focus', (e) => {
            const source = e.target.closest('.equation-source');
            if (source) {
                source.style.display = 'block';
                const display = source.nextElementSibling;
                if (display) {
                    display.style.display = 'none';
                }
            }
        }, true);

        this.editorDiv.addEventListener('blur', (e) => {
            const source = e.target.closest('.equation-source');
            if (source) {
                source.style.display = 'none';
                const display = source.nextElementSibling;
                if (display) {
                    display.style.display = 'block';
                }
            }
        }, true);
    }

    renderEquation(wrapper) {
        const source = wrapper.querySelector('.equation-source');
        const display = wrapper.querySelector('.latex-equation, .chemistry-equation');
        const isChemistry = display.classList.contains('chemistry-equation');
        
        if (source && display) {
            const content = source.textContent.trim();
            try {
                if (isChemistry) {
                    katex.render('\\ce{' + content + '}', display, {
                        throwOnError: false,
                        displayMode: true
                    });
                } else {
                    katex.render(content, display, {
                        throwOnError: false,
                        displayMode: true
                    });
                }
                display.style.display = 'block';
                source.style.display = 'none';
            } catch (e) {
                console.error('Render Error:', e);
                display.textContent = content;
            }
        }
    }

    init(options) {
        // Apply custom styles
        const styles = document.createElement('style');
        styles.textContent = `
            .custom-editor {
                border: 1px solid #ced4da;
                border-radius: 0.25rem;
                padding: 0.5rem;
                background: #fff;
            }
            .custom-editor:focus {
                border-color: #86b7fe;
                box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
                outline: 0;
            }
            .editor-toolbar {
                gap: 0.25rem;
            }
            .editor-toolbar button {
                min-width: 2.5rem;
            }
            .katex-display {
                background: white;
                padding: 10px;
                border-radius: 4px;
                margin: 10px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .katex {
                color: #000;
                background: white;
                padding: 2px 4px;
                border-radius: 2px;
            }
            .question-text .katex-display {
                background: white;
                padding: 10px;
                border-radius: 4px;
                margin: 10px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .question-text .katex {
                color: #000;
                background: white;
                padding: 2px 4px;
                border-radius: 2px;
            }
        `;
        document.head.appendChild(styles);
    }

    // Public methods
    getContent() {
        return this.editorDiv ? this.editorDiv.innerHTML : '';
    }

    setContent(html) {
        if (this.editorDiv) {
            this.editorDiv.innerHTML = html;
            // Re-render math in editor
            renderMathInElement(this.editorDiv, {
                delimiters: [
                    {left: "$$", right: "$$", display: true},
                    {left: "$", right: "$", display: false},
                    {left: "\\[", right: "\\]", display: true},
                    {left: "\\(", right: "\\)", display: false}
                ],
                throwOnError: false,
                trust: true
            });
        }
    }
}
