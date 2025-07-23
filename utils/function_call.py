from google.genai import types

# 1. Schema untuk Ekstraksi Seluruh Teks
# Opsi 1: Ekstrak semua teks dalam satu blok besar
extract_all_text_schema = types.Schema(
    type=types.Type.OBJECT,
    properties={
        'all_text': types.Schema(
            type=types.Type.STRING,
            description="Seluruh konten teks yang diekstrak dari halaman, digabungkan menjadi satu string."
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
    required=['all_text', 'explanation']
)

# 2. Schema untuk Flowchart
flowchart_schema = types.Schema(
    type=types.Type.OBJECT,
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
)

# Definisi Function Call Utama
analyze_document_page_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name='analyze_document_page',
            description="Menganalisis gambar halaman dokumen untuk mengekstrak seluruh teks, mengidentifikasi flowchart, dan membuat ringkasan.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    'page_number': types.Schema(
                        type=types.Type.STRING,
                        description='Nomor halaman yang terlihat di dokumen (cth: "1", "ii", "45", "cover" (jika tidak ada nomor halaman)).'
                    ),
                    'extracted_text': extract_all_text_schema,
                    'flowchart': flowchart_schema,
                },
                required=['page_number', 'extracted_text']
            )
        )
    ]
)

STRUCTURED_EXTRACTION_TOOL = [analyze_document_page_tool]