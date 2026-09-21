class DatasetLoader:
    """
    Raw -> CanonicalRecord loader for SireLLM's six finalized dataset families.

    Handwritten parsers/adapters perform source interpretation. Raw/source data
    remains separate from model-facing normalized content.
    """

    TINYSTORIES_DELIMITER = "<|endoftext|>"

    def __init__(
        self,
        json_parser,
        jsonl_parser,
        text_parser,
        CanonicalRecord,
        dailydialog_adapter,
        dolly_adapter,
        movie_adapter,
        siresoft_adapter,
        tinystories_adapter,
        openassistant_adapter,
    ):
        self.json_parser = json_parser
        self.jsonl_parser = jsonl_parser
        self.text_parser = text_parser
        self.CanonicalRecord = CanonicalRecord
        self.dailydialog_adapter = dailydialog_adapter
        self.dolly_adapter = dolly_adapter
        self.movie_adapter = movie_adapter
        self.siresoft_adapter = siresoft_adapter
        self.tinystories_adapter = tinystories_adapter
        self.openassistant_adapter = openassistant_adapter

    def default_sources(self, dataset_id):
        mapping = {
            "dailydialog": {
                "dialogues": "datasets/raw/dailydialog/dialogues.json",
                "ontology": "datasets/raw/dailydialog/ontology.json",
            },
            "dolly": {
                "instructions": "datasets/raw/dolly/databricks-dolly-15k.jsonl",
            },
            "movie-corpus": {
                "conversations": "datasets/raw/movie-corpus/conversations.json",
                "corpus": "datasets/raw/movie-corpus/corpus.json",
                "index": "datasets/raw/movie-corpus/index.json",
                "speakers": "datasets/raw/movie-corpus/speakers.json",
                "utterances": "datasets/raw/movie-corpus/utterances.jsonl",
            },
            "siresoft": {
                "knowledge": "datasets/raw/siresoft/siresoft.txt",
            },
            "tinystories": {
                "stories": "datasets/raw/tinystories/TinyStories-train.txt",
            },
            "openassistant": {
                "messages": "datasets/raw/openassistant/oasst1-ready.jsonl",
            },
        }

        if dataset_id not in mapping:
            raise ValueError(
                "unsupported dataset_id: "
                + str(dataset_id)
            )

        result = {}

        for key in mapping[dataset_id]:
            result[key] = mapping[
                dataset_id
            ][key]

        return result

    def load(self, dataset_id, sources=None):
        if not isinstance(dataset_id, str) or dataset_id == "":
            raise ValueError(
                "dataset_id must be non-empty str"
            )

        if sources is None:
            sources = self.default_sources(
                dataset_id
            )

        if not isinstance(sources, dict):
            raise TypeError(
                "sources must be dict or None"
            )

        if dataset_id == "dailydialog":
            return self._load_dailydialog(sources)

        if dataset_id == "dolly":
            return self._load_dolly(sources)

        if dataset_id == "movie-corpus":
            return self._load_movie(sources)

        if dataset_id == "siresoft":
            return self._load_siresoft(sources)

        if dataset_id == "tinystories":
            return self._load_tinystories(sources)

        if dataset_id == "openassistant":
            return self._load_openassistant(sources)

        raise ValueError(
            "unsupported dataset_id: "
            + dataset_id
        )

    def _load_dailydialog(self, sources):
        dialogue_path = self._require_source(
            sources,
            "dialogues",
        )

        root = self._read_json(
            dialogue_path
        )

        records = self._records_from_root(
            root,
            (
                "dialogues",
                "data",
                "records",
            ),
        )

        output = []
        index = 0

        while index < len(records):
            output.append(
                self.dailydialog_adapter.adapt_record(
                    records[index],
                    index,
                    source_file=dialogue_path,
                )
            )
            index += 1

        if "ontology" in sources:
            ontology = self._read_json(
                sources["ontology"]
            )

            output.append(
                self._auxiliary_record(
                    record_id="dailydialog-ontology",
                    dataset_id="dailydialog",
                    dataset_name="DailyDialog",
                    source_file=sources["ontology"],
                    source_format="json",
                    payload=ontology,
                    role="ontology",
                )
            )

        return output

    def _load_dolly(self, sources):
        path = self._require_source(
            sources,
            "instructions",
        )

        output = []
        index = 0

        for record in self.jsonl_parser.iter_file(
            path
        ):
            output.append(
                self.dolly_adapter.adapt_record(
                    record,
                    index,
                    source_file=path,
                )
            )

            index += 1

        return output

    def _load_movie(self, sources):
        """
        Load Cornell / ConvoKit movie-dialog data.

        The downloaded corpus stores utterances as JSONL. Conversation records
        may contain explicit utterance IDs, or may contain metadata only while
        each utterance carries its conversation_id. Both layouts are supported.
        """
        output = []
        utterance_map = {}
        utterances_by_conversation = {}

        if "utterances" in sources:
            utterance_path = sources[
                "utterances"
            ]

            if str(
                utterance_path
            ).lower().endswith(
                ".jsonl"
            ):
                utterances = []

                for record in (
                    self.jsonl_parser
                    .iter_file(
                        utterance_path
                    )
                ):
                    utterances.append(
                        self._deep_copy(
                            record
                        )
                    )

            else:
                utterance_root = (
                    self._read_json(
                        utterance_path
                    )
                )

                utterances = (
                    self._records_from_root(
                        utterance_root,
                        (
                            "utterances",
                            "data",
                            "records",
                        ),
                    )
                )

            index = 0

            while index < len(
                utterances
            ):
                utterance = (
                    utterances[
                        index
                    ]
                )

                output.append(
                    self.movie_adapter
                    .adapt_utterance(
                        utterance,
                        index,
                        source_file=(
                            utterance_path
                        ),
                    )
                )

                utterance_id = (
                    self
                    ._movie_utterance_id(
                        utterance
                    )
                )

                if (
                    utterance_id
                    is not None
                ):
                    utterance_map[
                        utterance_id
                    ] = (
                        self._deep_copy(
                            utterance
                        )
                    )

                conversation_id = (
                    self
                    ._movie_utterance_conversation_id(
                        utterance
                    )
                )

                if (
                    conversation_id
                    is not None
                ):
                    if (
                        conversation_id
                        not in
                        utterances_by_conversation
                    ):
                        utterances_by_conversation[
                            conversation_id
                        ] = []

                    utterances_by_conversation[
                        conversation_id
                    ].append(
                        self._deep_copy(
                            utterance
                        )
                    )

                index += 1

        conversation_path = (
            self._require_source(
                sources,
                "conversations",
            )
        )

        conversation_root = (
            self._read_json(
                conversation_path
            )
        )

        conversations = (
            self
            ._movie_conversations_from_root(
                conversation_root
            )
        )

        index = 0

        while index < len(
            conversations
        ):
            source_conversation = (
                conversations[
                    index
                ]
            )

            resolved = (
                self
                ._resolve_movie_conversation(
                    source_conversation,
                    utterance_map,
                    utterances_by_conversation,
                )
            )

            utterances = resolved.get(
                "utterances"
            )

            if (
                isinstance(
                    utterances,
                    list,
                )
                and len(
                    utterances
                ) > 0
            ):
                output.append(
                    self.movie_adapter
                    .adapt_conversation(
                        resolved,
                        index,
                        source_file=(
                            conversation_path
                        ),
                    )
                )

            else:
                # Preserve conversation metadata even when a source record has
                # no resolvable utterances. It remains non-training auxiliary
                # data instead of being silently dropped.
                conversation_id = (
                    self
                    ._movie_conversation_id(
                        source_conversation
                    )
                )

                output.append(
                    self._auxiliary_record(
                        record_id=(
                            "movie-conversation-"
                            + (
                                conversation_id
                                if conversation_id
                                is not None
                                else str(
                                    index
                                )
                            )
                        ),
                        dataset_id=(
                            "movie-corpus"
                        ),
                        dataset_name=(
                            "Cornell Movie Dialogs Corpus"
                        ),
                        source_file=(
                            conversation_path
                        ),
                        source_format=(
                            "json"
                        ),
                        payload=(
                            source_conversation
                        ),
                        role=(
                            "conversation_without_utterances"
                        ),
                    )
                )

            index += 1

        for role in (
            "corpus",
            "index",
            "speakers",
        ):
            if role in sources:
                payload = self._read_json(
                    sources[
                        role
                    ]
                )

                output.append(
                    self._auxiliary_record(
                        record_id=(
                            "movie-aux-"
                            + role
                        ),
                        dataset_id=(
                            "movie-corpus"
                        ),
                        dataset_name=(
                            "Cornell Movie Dialogs Corpus"
                        ),
                        source_file=(
                            sources[
                                role
                            ]
                        ),
                        source_format="json",
                        payload=payload,
                        role=role,
                    )
                )

        return output

    def _load_siresoft(self, sources):
        path = self._require_source(
            sources,
            "knowledge",
        )

        document = self.text_parser.parse_file(
            path
        )

        return [
            self.siresoft_adapter.adapt_document(
                document.content,
                index=0,
                source_file=path,
                source_metadata={
                    "line_count": document.line_count,
                    "character_count": document.character_count,
                    "byte_count": document.byte_count,
                },
            )
        ]

    def _load_tinystories(self, sources):
        path = self._require_source(
            sources,
            "stories",
        )

        document = self.text_parser.parse_file(
            path
        )

        text = document.content
        delimiter = self.TINYSTORIES_DELIMITER

        if delimiter not in text:
            return [
                self.tinystories_adapter.adapt_story(
                    text,
                    0,
                    source_file=path,
                    metadata={
                        "boundary_mode": "whole_file",
                        "source_start": 0,
                        "source_end": len(text),
                    },
                )
            ]

        output = []
        start = 0
        index = 0

        while start <= len(text):
            marker = text.find(
                delimiter,
                start,
            )

            if marker < 0:
                segment = text[start:]

                if segment != "":
                    record = self.tinystories_adapter.adapt_story(
                        segment,
                        index,
                        source_file=path,
                        metadata={
                            "boundary_mode": "explicit_endoftext",
                            "source_start": start,
                            "source_end": len(text),
                            "separator_after": "",
                        },
                    )

                    record.original_fields[
                        "separator_after"
                    ] = ""

                    output.append(
                        record
                    )

                break

            segment = text[
                start:marker
            ]

            record = self.tinystories_adapter.adapt_story(
                segment,
                index,
                source_file=path,
                metadata={
                    "boundary_mode": "explicit_endoftext",
                    "source_start": start,
                    "source_end": marker,
                    "separator_after": delimiter,
                },
            )

            record.original_fields[
                "separator_after"
            ] = delimiter

            output.append(
                record
            )

            index += 1
            start = marker + len(
                delimiter
            )

            if start == len(text):
                break

        return output

    def _load_openassistant(self, sources):
        path = self._require_source(
            sources,
            "messages",
        )

        groups = {}
        order = []
        ungrouped = []
        line_index = 0

        for record in self.jsonl_parser.iter_file(
            path
        ):
            tree_id = record.get(
                "message_tree_id",
                record.get(
                    "tree_id",
                    record.get(
                        "conversation_id"
                    ),
                ),
            )

            if tree_id is None or tree_id == "":
                ungrouped.append(
                    (
                        line_index,
                        record,
                    )
                )
            else:
                key = str(
                    tree_id
                )

                if key not in groups:
                    groups[key] = []
                    order.append(
                        key
                    )

                groups[key].append(
                    self._deep_copy(
                        record
                    )
                )

            line_index += 1

        output = []
        conversation_index = 0

        for key in order:
            output.append(
                self.openassistant_adapter.adapt_conversation(
                    groups[key],
                    conversation_index,
                    source_file=path,
                )
            )

            conversation_index += 1

        for source_index, record in ungrouped:
            output.append(
                self.openassistant_adapter.adapt_message(
                    record,
                    source_index,
                    source_file=path,
                )
            )

        return output

    def _auxiliary_record(
        self,
        record_id,
        dataset_id,
        dataset_name,
        source_file,
        source_format,
        payload,
        role,
    ):
        return self.CanonicalRecord(
            record_id=record_id,
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            source_file=source_file,
            source_record_index=0,
            source_format=source_format,
            raw_content=None,
            normalized_content=None,
            original_fields={
                "root": self._deep_copy(
                    payload
                ),
            },
            labels=[
                "auxiliary_metadata",
                role,
            ],
            language="unknown",
            document_type="auxiliary_metadata",
            source_type="public_dataset",
            provenance={
                "source_file": source_file,
                "role": role,
            },
            split="unsplit",
            metadata={
                "training_eligible": False,
                "auxiliary_role": role,
            },
        )

    def _read_json(self, path):
        handle = open(
            path,
            "r",
            encoding="utf-8",
        )

        try:
            text = handle.read()
        finally:
            handle.close()

        return self.json_parser.parse(
            text
        )

    def _records_from_root(
        self,
        root,
        preferred_keys,
    ):
        if isinstance(root, list):
            return [
                self._deep_copy(item)
                for item in root
            ]

        if isinstance(root, dict):
            for key in preferred_keys:
                value = root.get(key)

                if isinstance(value, list):
                    return [
                        self._deep_copy(item)
                        for item in value
                    ]

                if isinstance(value, dict):
                    return [
                        self._deep_copy(
                            value[item_key]
                        )
                        for item_key in value
                    ]

            values = []
            all_records = True

            for key in root:
                value = root[key]

                if not isinstance(value, dict):
                    all_records = False
                    break

                values.append(
                    self._deep_copy(
                        value
                    )
                )

            if all_records and len(values) > 0:
                return values

            return [
                self._deep_copy(
                    root
                )
            ]

        raise ValueError(
            "JSON dataset root must be list or dict"
        )

    def _resolve_movie_conversation(
        self,
        record,
        utterance_map,
        utterances_by_conversation=None,
    ):
        if not isinstance(
            record,
            dict,
        ):
            raise TypeError(
                "movie conversation must be dict"
            )

        resolved = self._deep_copy(
            record
        )

        explicit_resolved = False

        for key in (
            "utterances",
            "lines",
            "dialogue",
            "dialog",
            "turns",
            "utterance_ids",
            "utteranceIDs",
            "line_ids",
            "lineIDs",
        ):
            value = record.get(
                key
            )

            if not isinstance(
                value,
                list,
            ):
                continue

            if len(
                value
            ) == 0:
                continue

            if isinstance(
                value[
                    0
                ],
                dict,
            ):
                resolved[
                    "utterances"
                ] = self._deep_copy(
                    value
                )

                explicit_resolved = True
                break

            resolved_items = []
            all_found = True

            for item in value:
                item_key = str(
                    item
                )

                if (
                    item_key
                    not in utterance_map
                ):
                    all_found = False
                    break

                resolved_items.append(
                    self._deep_copy(
                        utterance_map[
                            item_key
                        ]
                    )
                )

            if (
                all_found
                and len(
                    resolved_items
                ) > 0
            ):
                resolved[
                    "_source_conversation"
                ] = self._deep_copy(
                    record
                )

                resolved[
                    "utterances"
                ] = resolved_items

                explicit_resolved = True
                break

        if (
            not explicit_resolved
            and isinstance(
                utterances_by_conversation,
                dict,
            )
        ):
            conversation_id = (
                self
                ._movie_conversation_id(
                    record
                )
            )

            if (
                conversation_id
                is not None
                and conversation_id
                in utterances_by_conversation
            ):
                resolved[
                    "_source_conversation"
                ] = self._deep_copy(
                    record
                )

                resolved[
                    "utterances"
                ] = self._deep_copy(
                    utterances_by_conversation[
                        conversation_id
                    ]
                )

        return resolved

    def _movie_conversations_from_root(
        self,
        root,
    ):
        if isinstance(
            root,
            list,
        ):
            return [
                self._deep_copy(
                    item
                )
                for item
                in root
            ]

        if not isinstance(
            root,
            dict,
        ):
            raise ValueError(
                "movie conversations root must be list or dict"
            )

        for key in (
            "conversations",
            "data",
            "records",
        ):
            value = root.get(
                key
            )

            if isinstance(
                value,
                list,
            ):
                return [
                    self._deep_copy(
                        item
                    )
                    for item
                    in value
                ]

            if isinstance(
                value,
                dict,
            ):
                return (
                    self
                    ._movie_conversations_from_mapping(
                        value
                    )
                )

        all_dicts = (
            len(
                root
            ) > 0
            and all(
                isinstance(
                    value,
                    dict,
                )
                for value
                in root.values()
            )
        )

        if all_dicts:
            return (
                self
                ._movie_conversations_from_mapping(
                    root
                )
            )

        return [
            self._deep_copy(
                root
            )
        ]

    def _movie_conversations_from_mapping(
        self,
        mapping,
    ):
        output = []

        for key in mapping:
            record = self._deep_copy(
                mapping[
                    key
                ]
            )

            if not isinstance(
                record,
                dict,
            ):
                continue

            if (
                self
                ._movie_conversation_id(
                    record
                )
                is None
            ):
                record[
                    "conversation_id"
                ] = str(
                    key
                )

            output.append(
                record
            )

        return output

    def _movie_conversation_id(
        self,
        record,
    ):
        if not isinstance(
            record,
            dict,
        ):
            return None

        for key in (
            "conversation_id",
            "conversationID",
            "conversationId",
            "id",
        ):
            if (
                key in record
                and record[
                    key
                ] is not None
                and record[
                    key
                ] != ""
            ):
                return str(
                    record[
                        key
                    ]
                )

        return None

    def _movie_utterance_conversation_id(
        self,
        record,
    ):
        if not isinstance(
            record,
            dict,
        ):
            return None

        for key in (
            "conversation_id",
            "conversationID",
            "conversationId",
            "conversation",
        ):
            if (
                key in record
                and record[
                    key
                ] is not None
                and record[
                    key
                ] != ""
            ):
                value = record[
                    key
                ]

                if isinstance(
                    value,
                    dict,
                ):
                    nested = (
                        self
                        ._movie_conversation_id(
                            value
                        )
                    )

                    if nested is not None:
                        return nested

                else:
                    return str(
                        value
                    )

        return None

    def _movie_utterance_id(self, record):
        if not isinstance(record, dict):
            return None

        for key in (
            "id",
            "utterance_id",
            "utteranceID",
            "line_id",
            "lineID",
        ):
            if key in record and record[key] is not None:
                return str(
                    record[key]
                )

        return None

    def _require_source(
        self,
        sources,
        role,
    ):
        if role not in sources:
            raise ValueError(
                "missing source role: "
                + role
            )

        path = sources[role]

        if not isinstance(path, str) or path == "":
            raise ValueError(
                "source path must be non-empty str"
            )

        return path

    def _deep_copy(self, value):
        if isinstance(value, dict):
            result = {}

            for key in value:
                result[key] = self._deep_copy(
                    value[key]
                )

            return result

        if isinstance(value, list):
            return [
                self._deep_copy(item)
                for item in value
            ]

        if isinstance(value, tuple):
            return [
                self._deep_copy(item)
                for item in value
            ]

        return value
