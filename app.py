"""Interface web locale Streamlit pour Stage Agent."""

import os
from datetime import datetime
from pathlib import Path
import re
import threading
from typing import List

import pandas as pd
import streamlit as st

from config.settings import settings
from main import run_job_search
from src.letters import LetterContext, LetterGenerator
from src.models import JobOffer
from src.spontaneous.campaign import load_target_companies
from src.spontaneous.mailer import SmtpMailer
from src.spontaneous.models import SpontaneousApplication
from src.spontaneous.pitch_generator import SpontaneousPitchGenerator
from src.spontaneous.tracker import SpontaneousTracker
from src.storage import CsvTracker, MarkdownTracker

st.set_page_config(
    page_title="Stage Agent — BUT 3 DATA/IA",
    page_icon="🎯",
    layout="wide",
)

OFFER_STATUSES = ["À contacter", "Candidaté", "Relancé", "Entretien", "Refusé", "Ignoré"]
SPONT_STATUSES = ["Prêt à envoyer (Dry-Run)", "Envoyé", "Relancé", "Réponse reçue", "Entretien", "Refusé"]
TARGET_COMPANIES_COLS = ["Nom", "Ville", "Departement", "Secteur", "Site_Web", "Email_Contact", "Note_Contexte"]


def _load_csv_df(path: Path, expected_cols: List[str], encoding: str = "utf-8-sig") -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=expected_cols)
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding=encoding, index_col=False)
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""
    return df[expected_cols].reset_index(drop=True)


def _save_csv_df(df: pd.DataFrame, path: Path, encoding: str = "utf-8-sig") -> None:
    df.to_csv(path, index=False, encoding=encoding)


def _sync_markdown_from_df(df: pd.DataFrame) -> None:
    """Reconstruit candidatures.md à partir du CSV édité."""
    offers: List[JobOffer] = []
    for _, row in df.iterrows():
        skills = [s.strip() for s in str(row.get("Compétences", "")).split(",") if s.strip()]
        try:
            score = int(float(row.get("Score") or 0))
        except ValueError:
            score = 0
        offers.append(
            JobOffer(
                id=str(row.get("ID", "")),
                title=str(row.get("Intitulé", "")),
                company=str(row.get("Entreprise", "")),
                location=str(row.get("Localisation", "")),
                is_remote=str(row.get("Télétravail", "")).strip().lower() == "oui",
                url=str(row.get("Lien", "")),
                source=str(row.get("Source", "")),
                published_at=str(row.get("Date", "")),
                detected_skills=skills,
                score=score,
                status=str(row.get("Statut", "À contacter")),
                personalized_pitch=str(row.get("Accroche", "")),
                letter_path=str(row.get("Lettre", "")),
            )
        )
    MarkdownTracker().generate_dashboard(offers)


def render_sidebar() -> None:
    candidate = settings.profile.get("candidate", {})
    search = settings.profile.get("search_criteria", {})
    cv_path = settings.cv_path

    with st.sidebar:
        st.title("🎯 Stage Agent")
        zones_display = ", ".join(settings.target_departments) or ", ".join(settings.target_locations) or "Toute la France"
        st.markdown(
            f"**{candidate.get('name', 'Profil non configuré')}**  \n"
            f"{candidate.get('degree', '')} — {candidate.get('school', '')}  \n"
            f"📅 {search.get('internship_period', '')}  \n"
            f"📍 Zones : `{zones_display}`"
        )

        st.divider()
        st.subheader("⚙️ État du système")
        if cv_path.exists():
            st.success(f"CV prêt : `{cv_path.name}`")
        else:
            st.warning("Aucun CV importé — ajoute ton CV dans l'onglet **⚙️ Mon Profil**")

        if settings.smtp.is_configured:
            st.success(f"SMTP prêt : `{settings.smtp.sender_email or settings.smtp.user}`")
        else:
            st.info("SMTP non configuré (brouillons manuels ou simulation Dry-Run)")

        st.divider()
        st.subheader("🔎 Lancer un scan d'offres")
        source_filter = st.selectbox(
            "Source",
            options=["all", "hellowork", "1jeune1solution", "web_search"],
            index=0,
        )
        min_score = st.slider("Score minimal", 20, 90, settings.min_score_threshold, step=5)
        limit = st.slider("Limite par source", 5, 50, settings.max_offers_per_source, step=5)

        if st.button("🚀 Lancer la collecte", type="primary", width="stretch"):
            with st.spinner("Collecte, filtrage et génération des lettres PDF en cours..."):
                new_offers = run_job_search(
                    source_filter=source_filter,
                    min_score=min_score,
                    limit=limit,
                )
            st.session_state["last_scan_msg"] = f"Scan terminé : {len(new_offers)} nouvelle(s) offre(s) ajoutée(s)."
            st.rerun()

        if st.session_state.get("last_scan_msg"):
            st.success(st.session_state["last_scan_msg"])

        st.divider()
        if st.button("⏻ Fermer l'application", width="stretch"):
            st.info("Arrêt de Stage Agent... Tu peux fermer cet onglet du navigateur.")
            threading.Timer(0.6, os._exit, args=[0]).start()


def render_offers_tab() -> None:
    st.header("🚀 Offres de stage publiées (Présentiel / Hybride)")

    full_df = _load_csv_df(settings.csv_output_path, CsvTracker.FIELDNAMES, encoding="utf-8-sig")
    if full_df.empty:
        st.info("Aucune offre enregistrée pour le moment. Utilise **🚀 Lancer la collecte** dans la barre latérale.")
        return

    full_df["Score"] = pd.to_numeric(full_df["Score"], errors="coerce").fillna(0).astype(int)

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total offres", len(full_df))
    c2.metric("Score ≥ 50", int((full_df["Score"] >= 50).sum()))
    c3.metric("À contacter", int((full_df["Statut"] == "À contacter").sum()))
    c4.metric(
        "En cours / Envoyées",
        int(full_df["Statut"].isin(["Candidaté", "Relancé", "Entretien"]).sum()),
    )

    # Filtres
    f1, f2, f3 = st.columns([2, 2, 3])
    avail_statuses = sorted(set(OFFER_STATUSES) | set(full_df["Statut"].unique()))
    selected_statuses = f1.multiselect("Filtrer par statut", options=avail_statuses, default=list(full_df["Statut"].unique()))
    avail_sources = sorted([s for s in full_df["Source"].unique() if s])
    selected_sources = f2.multiselect("Filtrer par source", options=avail_sources, default=avail_sources)
    query = f3.text_input("Rechercher (entreprise, poste, lieu, techno)", placeholder="Ex: Niort, Python, Atlantic...")

    mask = full_df["Statut"].isin(selected_statuses)
    if selected_sources:
        mask &= full_df["Source"].isin(selected_sources)
    if query.strip():
        q = query.strip().lower()
        haystack = (
            full_df["Entreprise"].str.lower()
            + " "
            + full_df["Intitulé"].str.lower()
            + " "
            + full_df["Localisation"].str.lower()
            + " "
            + full_df["Compétences"].str.lower()
        )
        mask &= haystack.str.contains(re.escape(q), na=False)

    filtered_df = full_df.loc[mask].copy().reset_index(drop=True)

    display_cols = [
        "Score",
        "Statut",
        "Intitulé",
        "Entreprise",
        "Localisation",
        "Télétravail",
        "Compétences",
        "Source",
        "Date",
        "Lien",
        "ID",
    ]
    edited_df = st.data_editor(
        filtered_df[display_cols],
        width="stretch",
        hide_index=True,
        disabled=[c for c in display_cols if c != "Statut"],
        column_config={
            "Score": st.column_config.NumberColumn("Score", format="%d", width="small"),
            "Statut": st.column_config.SelectboxColumn("Statut", options=OFFER_STATUSES, required=True),
            "Lien": st.column_config.LinkColumn("Offre", display_text="Ouvrir"),
            "ID": st.column_config.TextColumn("ID", width="small"),
        },
        key="offers_editor",
    )

    if st.button("💾 Enregistrer les changements de statut", key="save_offers_status"):
        status_map = dict(zip(edited_df["ID"], edited_df["Statut"]))
        full_df["Statut"] = full_df.apply(
            lambda r: status_map.get(r["ID"], r["Statut"]),
            axis=1,
        )
        _save_csv_df(full_df, settings.csv_output_path, encoding="utf-8-sig")
        _sync_markdown_from_df(full_df)
        st.success("Statuts enregistrés dans `candidatures.csv` et `candidatures.md`.")
        st.rerun()

    st.divider()
    st.subheader("📄 Détail de l'offre & Lettre de motivation PDF")

    if filtered_df.empty:
        st.info("Aucune offre ne correspond aux filtres actifs.")
        return

    offer_indices = list(filtered_df.index)
    selected_idx = st.selectbox(
        "Sélectionner une offre",
        options=offer_indices,
        format_func=lambda i: (
            f"[{filtered_df.loc[i, 'Score']} pts] {filtered_df.loc[i, 'Intitulé']} — "
            f"{filtered_df.loc[i, 'Entreprise']} ({filtered_df.loc[i, 'Localisation']})"
        ),
    )
    row = filtered_df.loc[selected_idx]

    col_info, col_actions = st.columns([3, 2])
    with col_info:
        st.markdown(
            f"**Entreprise :** {row['Entreprise']}  \n"
            f"**Lieu :** {row['Localisation']}  \n"
            f"**Compétences détectées :** `{row['Compétences'] or 'Non spécifié'}`  \n"
            f"**Source :** {row['Source']} | **Statut :** `{row['Statut']}`  \n"
            f"**Lien :** [{row['Lien']}]({row['Lien']})"
        )

    letter_file = Path(row["Lettre"]) if row.get("Lettre") else None
    with col_actions:
        if st.button("🔄 Régénérer la lettre PDF", key="regen_offer_letter"):
            ctx = LetterContext(
                company=row["Entreprise"],
                address=re.sub(r"^\d{2,3}\s*-\s*", "", str(row["Localisation"])),
                job_title=re.sub(r"\s*\((H/F|F/H)\)\s*", " ", str(row["Intitulé"])).strip(),
                offer_skills=[s.strip() for s in str(row["Compétences"]).split(",") if s.strip()],
                file_stem=f"{row['Entreprise']}_{str(row['ID'])[:6]}",
            )
            gen = LetterGenerator()
            new_path = gen.export_pdf(ctx)
            full_df.loc[full_df["ID"] == row["ID"], "Lettre"] = str(new_path)
            full_df.loc[full_df["ID"] == row["ID"], "Accroche"] = gen.render(ctx).replace("\n", " ")
            _save_csv_df(full_df, settings.csv_output_path, encoding="utf-8-sig")
            st.success(f"Lettre régénérée : `{new_path.name}`")
            st.rerun()

        if letter_file and letter_file.exists():
            st.download_button(
                "📥 Télécharger la lettre PDF",
                data=letter_file.read_bytes(),
                file_name=letter_file.name,
                mime="application/pdf",
                width="stretch",
            )
        else:
            st.caption("Aucune lettre PDF trouvée pour cette ligne — clique sur Régénérer.")

    with st.expander("Voir le texte de la lettre associée"):
        ctx_preview = LetterContext(
            company=row["Entreprise"],
            address=re.sub(r"^\d{2,3}\s*-\s*", "", str(row["Localisation"])),
            job_title=re.sub(r"\s*\((H/F|F/H)\)\s*", " ", str(row["Intitulé"])).strip(),
            offer_skills=[s.strip() for s in str(row["Compétences"]).split(",") if s.strip()],
        )
        st.text(LetterGenerator().render(ctx_preview))


def render_spontaneous_tab() -> None:
    st.header("📬 Candidatures Spontanées & Relances J+7")
    tracker = SpontaneousTracker()
    companies = load_target_companies()
    companies_by_name = {c.name.strip().lower(): c for c in companies}

    # 1. Relances J+7 dues
    st.subheader("🔔 Relances J+7 à effectuer")
    due_rows = tracker.get_due_followups()
    if not due_rows:
        st.success("Aucune relance J+7 arrivée à échéance pour le moment.")
    else:
        st.warning(f"{len(due_rows)} entreprise(s) au statut 'Envoyé' ont atteint ou dépassé la date de relance J+7.")
        st.dataframe(pd.DataFrame(due_rows)[["Entreprise", "Ville", "Email", "Date_Envoi", "Date_Relance_Prevue"]], width="stretch", hide_index=True)

        c_dry, c_live = st.columns(2)
        if c_dry.button("🧪 Simuler les relances (Dry-Run)", key="relance_dry"):
            gen = SpontaneousPitchGenerator()
            letter_gen = LetterGenerator()
            mailer = SmtpMailer(dry_run=True)
            for r in due_rows:
                meta = companies_by_name.get(r["Entreprise"].strip().lower())
                app = gen.generate_followup(r["Entreprise"], r["Ville"], r["Email"], r["Date_Envoi"], r.get("Commentaires", ""))
                ctx = LetterContext(company=re.sub(r"\s*\(.*?\)", "", r["Entreprise"]).strip(), address=r["Ville"], sector=meta.sector if meta else "")
                app.letter_path = str(letter_gen.export_pdf(ctx))
                mailer.send_application(app)
            st.info(f"Simulation terminée pour {len(due_rows)} relance(s). Aucun e-mail envoyé.")

        confirm_relance = c_live.checkbox("Confirmer l'envoi réel des relances J+7 via SMTP", key="confirm_relance_cb")
        if c_live.button(
            "📨 Envoyer les relances J+7 (SMTP réel)",
            disabled=(not confirm_relance or not settings.smtp.is_configured),
            type="primary",
            key="relance_send",
        ):
            gen = SpontaneousPitchGenerator()
            letter_gen = LetterGenerator()
            mailer = SmtpMailer(dry_run=False)
            succeeded = []
            with st.spinner("Envoi des relances en cours (temporisation anti-spam active)..."):
                for r in due_rows:
                    meta = companies_by_name.get(r["Entreprise"].strip().lower())
                    app = gen.generate_followup(r["Entreprise"], r["Ville"], r["Email"], r["Date_Envoi"], r.get("Commentaires", ""))
                    ctx = LetterContext(company=re.sub(r"\s*\(.*?\)", "", r["Entreprise"]).strip(), address=r["Ville"], sector=meta.sector if meta else "")
                    app.letter_path = str(letter_gen.export_pdf(ctx))
                    if mailer.send_application(app):
                        succeeded.append(r["Entreprise"])
            if succeeded:
                tracker.mark_followed_up(succeeded)
            st.success(f"{len(succeeded)}/{len(due_rows)} relance(s) envoyée(s) et marquée(s) 'Relancé'.")
            st.rerun()

    st.divider()

    # 2. Campagne spontanée
    st.subheader("🚀 Lancer une vague de candidatures spontanées")
    avail_depts = sorted({c.department for c in companies if c.department})
    dept_choice = st.selectbox("Filtrer par département", ["Tous"] + avail_depts)
    selected_companies = (
        companies if dept_choice == "Tous" else [c for c in companies if c.department == dept_choice]
    )

    if not selected_companies:
        st.info("Aucune entreprise dans `data/target_companies.csv` pour ce filtre.")
    else:
        st.caption(f"{len(selected_companies)} entreprise(s) sélectionnée(s).")
        preview_comp = st.selectbox(
            "Prévisualiser le mail et la lettre pour :",
            options=selected_companies,
            format_func=lambda c: f"{c.name} ({c.city} - {c.department}) <{c.contact_email}>",
        )
        pitch_gen = SpontaneousPitchGenerator()
        letter_gen = LetterGenerator()
        preview_app = pitch_gen.generate_application(preview_comp)
        preview_ctx = LetterContext(
            company=re.sub(r"\s*\(.*?\)", "", preview_comp.name).strip(),
            address=preview_comp.city,
            sector=preview_comp.sector,
        )
        with st.expander("👁️ Aperçu de l'e-mail et de la lettre jointe"):
            st.markdown(f"**Objet :** `{preview_app.subject}`")
            st.text(preview_app.body)
            m1, m2 = st.columns(2)
            m1.link_button(
                "📧 Ouvrir le brouillon dans ma messagerie",
                SmtpMailer.build_mailto_url(preview_app),
                width="stretch",
            )
            if m2.button("📄 Générer la lettre PDF pour cette entreprise", key="gen_single_spont_pdf", width="stretch"):
                pdf_p = letter_gen.export_pdf(preview_ctx)
                st.session_state["single_spont_pdf"] = str(pdf_p)
            saved_spont = st.session_state.get("single_spont_pdf")
            if saved_spont and Path(saved_spont).exists():
                sp = Path(saved_spont)
                st.download_button(
                    f"📥 Télécharger {sp.name}",
                    data=sp.read_bytes(),
                    file_name=sp.name,
                    mime="application/pdf",
                )
            st.markdown("**Lettre PDF générée :**")
            st.text(letter_gen.render(preview_ctx))

        b1, b2 = st.columns(2)
        if b1.button("🧪 Simuler la campagne (Dry-Run)", key="spont_dry", width="stretch"):
            apps: List[SpontaneousApplication] = []
            mailer = SmtpMailer(dry_run=True)
            with st.spinner("Génération des lettres PDF et simulation..."):
                for c in selected_companies:
                    app = pitch_gen.generate_application(c)
                    ctx = LetterContext(company=re.sub(r"\s*\(.*?\)", "", c.name).strip(), address=c.city, sector=c.sector)
                    app.letter_path = str(letter_gen.export_pdf(ctx))
                    mailer.send_application(app)
                    apps.append(app)
            tracker.record_applications(apps, mark_as_sent=False)
            st.success(f"Simulation terminée pour {len(apps)} entreprise(s). `suivi_spontanees.csv` mis à jour.")
            st.rerun()

        confirm_send = b2.checkbox(
            "Je confirme avoir vérifié les e-mails des destinataires et vouloir envoyer ces candidatures maintenant",
            key="confirm_spont_send",
        )
        if b2.button(
            "🚀 Envoyer la campagne (SMTP réel)",
            disabled=(not confirm_send or not settings.smtp.is_configured),
            type="primary",
            key="spont_send",
            width="stretch",
        ):
            existing = tracker.load_existing()
            to_send = [
                c
                for c in selected_companies
                if (existing.get(c.name.strip().lower(), {}).get("Statut") or "").strip()
                not in tracker.ADVANCED_STATUSES
            ]
            if not to_send:
                st.info("Toutes les entreprises de ce filtre ont déjà un statut avancé (Envoyé / Relancé / Entretien...).")
            else:
                mailer = SmtpMailer(dry_run=False)
                succeeded_apps: List[SpontaneousApplication] = []
                with st.spinner(f"Envoi SMTP en cours pour {len(to_send)} entreprise(s)..."):
                    for c in to_send:
                        app = pitch_gen.generate_application(c)
                        ctx = LetterContext(company=re.sub(r"\s*\(.*?\)", "", c.name).strip(), address=c.city, sector=c.sector)
                        app.letter_path = str(letter_gen.export_pdf(ctx))
                        if mailer.send_application(app):
                            succeeded_apps.append(app)
                if succeeded_apps:
                    tracker.record_applications(succeeded_apps, mark_as_sent=True)
                st.success(f"{len(succeeded_apps)}/{len(to_send)} candidature(s) envoyée(s) et planifiée(s) à J+7.")
                st.rerun()

    st.divider()

    # 3. Suivi des spontanées
    st.subheader("📊 Tableau de suivi (`suivi_spontanees.csv`)")
    suivi_df = _load_csv_df(settings.spontaneous_csv_path, SpontaneousTracker.FIELDNAMES, encoding="utf-8-sig")
    edited_suivi = st.data_editor(
        suivi_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Statut": st.column_config.SelectboxColumn("Statut", options=SPONT_STATUSES, required=True),
        },
        key="suivi_spont_editor",
    )
    if st.button("💾 Sauvegarder suivi_spontanees.csv", key="save_suivi_spont"):
        _save_csv_df(edited_suivi, settings.spontaneous_csv_path, encoding="utf-8-sig")
        offers_df = _load_csv_df(settings.csv_output_path, CsvTracker.FIELDNAMES, encoding="utf-8-sig")
        _sync_markdown_from_df(offers_df)
        st.success("`suivi_spontanees.csv` et `candidatures.md` sauvegardés.")

    st.divider()

    # 4. Base d'entreprises cibles
    st.subheader("🏢 Base d'entreprises cibles (`data/target_companies.csv`)")
    st.caption("Vérifie ou corrige les adresses e-mail avant tout envoi réel. Tu peux ajouter ou supprimer des lignes.")
    targets_df = _load_csv_df(settings.target_companies_path, TARGET_COMPANIES_COLS, encoding="utf-8")
    edited_targets = st.data_editor(
        targets_df,
        width="stretch",
        hide_index=True,
        num_rows="dynamic",
        key="targets_editor",
    )
    if st.button("💾 Sauvegarder target_companies.csv", key="save_targets"):
        cleaned = edited_targets[edited_targets["Nom"].str.strip() != ""].copy()
        _save_csv_df(cleaned, settings.target_companies_path, encoding="utf-8")
        st.success(f"{len(cleaned)} entreprise(s) enregistrée(s) dans `data/target_companies.csv`.")


def render_letter_tab() -> None:
    st.header("✉️ Générateur de lettre à la carte")
    c1, c2 = st.columns(2)
    company = c1.text_input("Nom de l'entreprise *", placeholder="Ex: Sellsy")
    address = c2.text_input("Adresse ou ville", placeholder="Ex: 17000 La Rochelle")
    sector = c1.text_input("Secteur d'activité", placeholder="Ex: Éditeur logiciel SaaS, assurance, ESN, data...")
    job_title = c2.text_input("Intitulé du poste (optionnel)", placeholder="Ex: Stage Développeur Data / Python")
    skills_raw = st.text_input("Technos de l'offre à mettre en avant (séparées par des virgules)", placeholder="Ex: Python, SQL, Elasticsearch, PowerBI")

    skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
    ctx = LetterContext(
        company=company.strip() or "{nom entreprise}",
        address=address.strip(),
        sector=sector.strip(),
        job_title=job_title.strip(),
        offer_skills=skills,
    )
    gen = LetterGenerator()

    st.subheader("Aperçu du texte")
    st.text_area("Contenu généré", value=gen.render(ctx), height=380, disabled=True)

    if st.button("📄 Générer le PDF", type="primary", disabled=(not company.strip())):
        pdf_path = gen.export_pdf(ctx)
        st.session_state["custom_letter_path"] = str(pdf_path)
        st.success(f"Lettre PDF créée : `{pdf_path}`")

    saved_path = st.session_state.get("custom_letter_path")
    if saved_path and Path(saved_path).exists():
        p = Path(saved_path)
        st.download_button(
            f"📥 Télécharger {p.name}",
            data=p.read_bytes(),
            file_name=p.name,
            mime="application/pdf",
        )


def render_daily_tab() -> None:
    st.header("⏰ Veille Quotidienne & Modèle de Lettre")

    st.subheader("📋 Dernière veille exécutée")
    summary_path = settings.project_root / "logs" / "derniere_veille.txt"
    if summary_path.exists():
        st.code(summary_path.read_text(encoding="utf-8"), language="text")
    else:
        st.info("Aucun résumé de veille trouvé (`logs/derniere_veille.txt`).")

    log_files = sorted((settings.project_root / "logs").glob("veille_*.log"), reverse=True)
    if log_files:
        latest_log = log_files[0]
        with st.expander(f"Journal récent : {latest_log.name}"):
            lines = latest_log.read_text(encoding="utf-8", errors="replace").splitlines()
            st.code("\n".join(lines[-40:]), language="text")

    c1, c2 = st.columns(2)
    if c1.button("▶ Exécuter run_daily.py maintenant"):
        import run_daily
        with st.spinner("Exécution de la veille quotidienne..."):
            code = run_daily.main()
        if code == 0:
            st.success("Veille quotidienne exécutée et journalisée.")
            st.rerun()
        else:
            st.error("La veille a échoué — consulte le journal ci-dessus.")

    with c2:
        st.markdown(
            "**Tâche planifiée Windows (PowerShell) :**\n"
            "```powershell\n"
            "powershell -ExecutionPolicy Bypass -File scripts\\register_daily_task.ps1 -Time \"08:00\"\n"
            "```"
        )

    st.divider()
    st.subheader("📝 Modèle de lettre (`data/lettre_type.txt`)")
    template_path = settings.data_dir / "lettre_type.txt"
    current_template = template_path.read_text(encoding="utf-8") if template_path.exists() else ""
    new_template = st.text_area("Éditer le modèle (conserve les balises `{...}`)", value=current_template, height=340)
    if st.button("💾 Enregistrer data/lettre_type.txt"):
        template_path.write_text(new_template, encoding="utf-8")
        st.success("Modèle `data/lettre_type.txt` mis à jour.")


def render_profile_tab() -> None:
    st.header("⚙️ Mon Profil & Paramètres")
    profile = settings.profile
    cand = profile.get("candidate", {})
    search = profile.get("search_criteria", {})
    skills = profile.get("skills", {})

    with st.form("profile_form"):
        st.subheader("👤 Identité & Formation")
        c1, c2 = st.columns(2)
        name = c1.text_input("Prénom et Nom *", value=cand.get("name", ""))
        email = c2.text_input("Adresse e-mail *", value=cand.get("email", ""))
        phone = c1.text_input("Téléphone", value=cand.get("phone", ""))
        location = c2.text_input("Adresse / Ville", value=cand.get("location", ""))
        degree = c1.text_input("Formation / Niveau", value=cand.get("degree", ""))
        specialty = c2.text_input("Spécialité", value=cand.get("specialty", ""))
        school = c1.text_input("École / Université", value=cand.get("school", ""))
        period = c2.text_input("Période de stage souhaitée", value=search.get("internship_period", ""))

        st.subheader("🔎 Critères de recherche & Filtres")
        k1, k2 = st.columns(2)
        keywords_raw = k1.text_input(
            "Mots-clés de recherche (séparés par des virgules)",
            value=", ".join(search.get("search_keywords", [])),
            help="Ex: marketing, communication, digital",
        )
        locs_raw = k2.text_input(
            "Villes / régions cibles (séparées par des virgules)",
            value=", ".join(search.get("target_locations", [])),
            help="Ex: Paris, Lyon, Nantes",
        )
        depts_raw = k1.text_input(
            "Codes départements (séparés par des virgules)",
            value=", ".join(str(d) for d in search.get("target_departments", [])),
            help="Ex: 75, 92, 69 (laisser vide pour toute la France)",
        )
        excluded_raw = k2.text_input(
            "Mots à exclure des intitulés (optionnel, séparés par des virgules)",
            value=", ".join(search.get("excluded_title_keywords", [])),
        )

        f1, f2, f3 = st.columns(3)
        excl_alt = f1.checkbox("Stages uniquement (exclure alternances)", value=bool(search.get("exclude_alternance", True)))
        no_full_remote = f2.checkbox("Exclure le 100 % télétravail", value=bool(search.get("disallow_full_remote", True)))
        excl_non_tech = f3.checkbox("Exclure les métiers non-tech (mode IT/Data)", value=bool(search.get("exclude_non_tech", True)))

        st.subheader("🛠️ Compétences & Atouts (pour le scoring et les lettres)")
        s1, s2 = st.columns(2)
        core_raw = s1.text_input(
            "Compétences principales (+10 pts)",
            value=", ".join(skills.get("core", [])),
        )
        sec_raw = s2.text_input(
            "Compétences complémentaires (+5 pts)",
            value=", ".join(skills.get("secondary", [])),
        )
        exp_summary = st.text_area(
            "Résumé de tes expériences (utilisé si ton modèle de lettre contient `{experience_resume}`)",
            value=cand.get("experience_summary", ""),
            height=80,
        )
        project_highlight = st.text_area(
            "Projet marquant à mettre en avant dans la lettre (optionnel)",
            value=cand.get("project_highlight", ""),
            height=80,
        )

        if st.form_submit_button("💾 Enregistrer mon profil", type="primary"):
            def _split(txt: str) -> List[str]:
                return [x.strip() for x in txt.split(",") if x.strip()]

            new_profile = dict(profile)
            new_profile["candidate"] = {
                **cand,
                "name": name.strip(),
                "email": email.strip(),
                "phone": phone.strip(),
                "location": location.strip(),
                "degree": degree.strip(),
                "specialty": specialty.strip(),
                "school": school.strip(),
                "experience_summary": exp_summary.strip(),
                "project_highlight": project_highlight.strip(),
            }
            new_profile["search_criteria"] = {
                **search,
                "internship_period": period.strip(),
                "search_keywords": _split(keywords_raw),
                "target_locations": _split(locs_raw),
                "target_departments": _split(depts_raw),
                "excluded_title_keywords": _split(excluded_raw),
                "exclude_alternance": excl_alt,
                "disallow_full_remote": no_full_remote,
                "allow_remote": not no_full_remote,
                "exclude_non_tech": excl_non_tech,
            }
            new_profile["skills"] = {
                **skills,
                "core": _split(core_raw),
                "secondary": _split(sec_raw),
            }
            settings.save_profile(new_profile)
            st.success("Profil enregistré et appliqué immédiatement.")
            st.rerun()

    st.divider()
    st.subheader("📎 Mon CV (PDF)")
    uploaded_cv = st.file_uploader("Importer ou remplacer mon CV au format PDF", type=["pdf"])
    if uploaded_cv is not None:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        dest_cv = settings.data_dir / "cv.pdf"
        dest_cv.write_bytes(uploaded_cv.getvalue())
        updated = dict(settings.profile)
        updated.setdefault("candidate", {})["cv_filename"] = "data/cv.pdf"
        settings.save_profile(updated)
        st.success("CV enregistré (`data/cv.pdf`). Il sera joint automatiquement à tes envois.")
        st.rerun()

    st.divider()
    with st.expander("📧 Configuration e-mail automatique (SMTP — optionnel)"):
        st.caption(
            "Nécessaire uniquement pour l'envoi automatique en masse. "
            "Sinon, utilise le bouton « Ouvrir le brouillon dans ma messagerie » dans l'onglet Spontanées."
        )
        with st.form("smtp_form"):
            sc1, sc2 = st.columns(2)
            smtp_host = sc1.text_input("Serveur SMTP", value=settings.smtp.host)
            smtp_port = sc2.number_input("Port SMTP", min_value=1, max_value=65535, value=int(settings.smtp.port))
            smtp_user = sc1.text_input("E-mail de connexion", value=settings.smtp.user or "")
            smtp_pass = sc2.text_input("Mot de passe d'application", value=settings.smtp.password or "", type="password")
            sender_name = sc1.text_input("Nom affiché", value=settings.smtp.sender_name or cand.get("name", ""))
            sender_email = sc2.text_input("E-mail expéditeur", value=settings.smtp.sender_email or cand.get("email", ""))
            if st.form_submit_button("💾 Enregistrer la config SMTP"):
                settings.save_smtp_config(smtp_host, int(smtp_port), smtp_user, smtp_pass, sender_email, sender_name)
                st.success("Paramètres SMTP enregistrés dans `.env`.")
                st.rerun()

    st.divider()
    with st.expander("🔄 Réinitialiser mes tableaux (nouveau départ / nouvel utilisateur)"):
        st.warning("Supprime toutes les offres et suivis actuels (`candidatures.csv`, `suivi_spontanees.csv`, `letters/*.pdf`).")
        confirm_reset = st.checkbox("Je confirme vouloir repartir de zéro", key="confirm_reset_all")
        if st.button("🗑️ Tout réinitialiser", disabled=not confirm_reset):
            settings.csv_output_path.write_text(",".join(CsvTracker.FIELDNAMES) + "\n", encoding="utf-8-sig")
            settings.spontaneous_csv_path.write_text(",".join(SpontaneousTracker.FIELDNAMES) + "\n", encoding="utf-8-sig")
            letters_dir = settings.project_root / "letters"
            if letters_dir.exists():
                for pdf in letters_dir.glob("*.pdf"):
                    pdf.unlink()
            MarkdownTracker().generate_dashboard([])
            st.success("Tableaux et lettres réinitialisés.")
            st.rerun()


def main() -> None:
    render_sidebar()
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "🚀 Offres Publiées",
            "📬 Spontanées & Relances J+7",
            "✉️ Lettre à la Carte",
            "⏰ Veille & Modèle",
            "⚙️ Mon Profil",
        ]
    )
    with tab1:
        render_offers_tab()
    with tab2:
        render_spontaneous_tab()
    with tab3:
        render_letter_tab()
    with tab4:
        render_daily_tab()
    with tab5:
        render_profile_tab()


if __name__ == "__main__":
    main()
