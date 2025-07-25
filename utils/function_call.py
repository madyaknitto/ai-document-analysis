from google.genai import types

# Definisi Function Call Utama
analyze_document_page_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name='analyze_document_page',
            description="Menganalisis gambar halaman dokumen untuk mengekstrak konten sesuai dengan isi halaman. Jika halaman berisi flowchart, ekstrak flowchart saja. Jika halaman berisi teks biasa, ekstrak teks saja. Jika halaman berisi keduanya, ekstrak keduanya secara terpisah.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    'page_number': types.Schema(
                        type=types.Type.STRING,
                        description='Nomor halaman yang terlihat di dokumen (cth: "1", "ii", "45", "cover" (jika tidak ada nomor halaman)).'
                    ),
                    'extracted_text': types.Schema(
                        type=types.Type.OBJECT,
                        description="Ekstrak teks jika halaman berisi teks biasa (bukan flowchart). Jika halaman hanya berisi flowchart, biarkan null.",
                        properties={
                            'text': types.Schema(
                                type=types.Type.STRING,
                                description="Seluruh konten teks yang diekstrak dari halaman, digabungkan menjadi satu string. Hanya isi jika halaman berisi teks biasa."
                            ),
                            'explanation': types.Schema(
                                type=types.Type.STRING,
                                description=(
                                    "Penjelasan mengenai isi dan konteks halaman berdasarkan teks yang diekstrak. "
                                    "Identifikasi apakah halaman merupakan cover, halaman judul, daftar isi, daftar gambar, isi utama, atau lampiran. "
                                    "Jika ditemukan elemen seperti kode BRD, status dokumen, judul diapit tanda kurung, daftar fitur/kode, serta label dokumen seperti 'Business Requirements Document', maka klasifikasikan sebagai halaman cover atau halaman judul."
                                )
                            )
                        },
                        required=['text', 'explanation']
                    ),
                    'flowchart': types.Schema(
                        type=types.Type.OBJECT,
                        description="Ekstrak flowchart jika halaman berisi diagram alur. Jika halaman hanya berisi teks biasa, biarkan null.",
                        properties={
                            'title': types.Schema(type=types.Type.STRING, description='Judul flowchart, jika ada (cth: "Gambar 1. Alur Proses").'),
                            'nodes': types.Schema(
                                type=types.Type.ARRAY,
                                description="Setiap simpul (bentuk) dalam diagram.",
                                items=types.Schema(
                                    type=types.Type.OBJECT,
                                    properties={
                                        'id': types.Schema(type=types.Type.STRING, description='ID unik untuk node, cth: "node_1".'),
                                        'label': types.Schema(type=types.Type.STRING, description='Teks di dalam node.'),
                                        'shape': types.Schema(type=types.Type.STRING, description='Bentuk node (cth: "rectangle", "diamond").')
                                    },
                                    required=['id', 'label', 'shape']
                                )
                            ),
                            'edges': types.Schema(
                                type=types.Type.ARRAY,
                                description="Garis atau panah yang menghubungkan antar node.",
                                items=types.Schema(
                                    type=types.Type.OBJECT,
                                    properties={
                                        'from_node': types.Schema(type=types.Type.STRING, description='ID node asal.'),
                                        'to_node': types.Schema(type=types.Type.STRING, description='ID node tujuan.'),
                                        'label': types.Schema(type=types.Type.STRING, description='Teks pada garis penghubung jika ada.')
                                    },
                                    required=['from_node', 'to_node']
                                )
                            ),
                            'explanation': types.Schema(type=types.Type.STRING, description='Penjelasan detail mengenai alur proses yang digambarkan oleh flowchart.')
                        },
                        required=['title', 'nodes', 'edges', 'explanation']
                    ),
                },
                required=['page_number']
            )
        )
    ]
)

STRUCTURED_EXTRACTION_TOOL = [analyze_document_page_tool]