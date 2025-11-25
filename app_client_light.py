import streamlit as st
import pandas as pd
from typing import List, Dict
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

def is_processed_file(df: pd.DataFrame) -> bool:
    """Check if the uploaded file has all required columns"""
    required_columns = [
        'theme_principal', 
        'sous_theme',
        'date',
        'conversationId',
        'turn_count',
        'default_count',
        'feedbackPositive',
        'feedbackNegative'
    ]
    # Language columns are optional but preferred
    return all(col in df.columns for col in required_columns)

def display_statistics(df: pd.DataFrame):
    """Display simplified statistics focused on themes"""
    if df.empty:
        st.info("📊 Aucune donnée disponible pour les statistiques des thèmes.")
        return
        
    if 'theme_principal' not in df.columns or 'sous_theme' not in df.columns:
        st.info("📊 Les colonnes de thèmes ne sont pas disponibles dans les données.")
        return
        
    try:
        # Calculate how many conversations have theme data
        total_conversations = len(df)
        has_theme = df['theme_principal'].notna() & (df['theme_principal'] != "")
        theme_conversations = has_theme.sum()
        theme_percentage = (theme_conversations / total_conversations * 100).round(1)
        
        # Display theme statistics with conversation count
        st.subheader(f"📊 Statistiques des thèmes ({theme_conversations}/{total_conversations} conversations - {theme_percentage}%)")
        
        # Display metrics in columns
        col1, col2 = st.columns(2)
        col1.metric("Conversations avec thème", theme_conversations)
        col2.metric("Pourcentage du total", f"{theme_percentage}%")
        
        # Répartition des thèmes et sous-thèmes
        theme_data = df.groupby(['theme_principal', 'sous_theme']).size().reset_index(name='count')
        
        if theme_data.empty:
            st.info("Aucune donnée de thème disponible.")
            return
            
        theme_data['percentage'] = (theme_data['count'] / len(df) * 100).round(1)
        
        # Calculer les totaux par thème
        theme_totals = theme_data.groupby('theme_principal')['count'].sum().sort_values(ascending=False)
        
        # Créer un tableau avec les thèmes et sous-thèmes
        table_data = []
        
        for theme in theme_totals.index:
            theme_rows = theme_data[theme_data['theme_principal'] == theme].sort_values('count', ascending=False)
            theme_total = theme_totals[theme]
            theme_percentage = (theme_total / len(df) * 100).round(1)
            
            first_row = True
            for _, row in theme_rows.iterrows():
                table_data.append([
                    f"{theme} ({theme_percentage}%)" if first_row else "",
                    f"{row['sous_theme']} ({row['percentage']}%)",
                    f"{row['count']}"
                ])
                first_row = False
        
        theme_table_df = pd.DataFrame(
            table_data,
            columns=["Thématique", "Sous-catégorie", "Nombre de conversations"]
        )
        
        st.dataframe(
            theme_table_df,
            hide_index=True,
            column_config={
                "Thématique": st.column_config.TextColumn("Thématique", width="large"),
                "Sous-catégorie": st.column_config.TextColumn("Sous-catégorie", width="large"),
                "Nombre de conversations": st.column_config.NumberColumn("Nombre de conversations")
            }
        )
        
    except Exception as e:
        st.info("Une erreur est survenue lors de l'affichage des statistiques des thèmes.")

def display_conversation_metrics(df: pd.DataFrame):
    """Display conversation and message metrics with timeline visualization"""
    if df.empty:
        st.info("📈 Aucune donnée disponible pour les métriques de conversation.")
        return
        
    required_columns = ['date', 'conversationId', 'turn_count']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.info(f"📈 Certaines colonnes requises ne sont pas disponibles : {', '.join(missing_columns)}")
        return
    
    try:
        st.subheader("📈 Métriques des conversations")
        
        # Ensure date column is datetime
        df['date'] = pd.to_datetime(df['date'], format='ISO8601').dt.normalize()
        
        # Calculate basic metrics
        total_conversations = len(df)
        total_messages = df['turn_count'].sum() if 'turn_count' in df.columns else total_conversations
        
        # Display metrics in columns
        col1, col2 = st.columns(2)
        col1.metric("Nombre total de conversations", total_conversations)
        col2.metric("Nombre total de messages utilisateur", int(total_messages))
        
        # Group data by date
        daily_data = df.groupby('date').agg({
            'conversationId': 'count',
            'turn_count': 'sum'
        }).reset_index()
        
        if daily_data.empty:
            st.info("Aucune donnée quotidienne disponible.")
            return
        
        # Sort by date
        daily_data = daily_data.sort_values('date')
        
        # Format date for display
        daily_data['date_formatted'] = daily_data['date'].dt.strftime('%d/%m/%Y')
        
        # Display daily data table
        st.subheader("📅 Données quotidiennes")
        st.dataframe(
            daily_data[['date_formatted', 'conversationId', 'turn_count']].rename(columns={
                'date_formatted': 'Date',
                'conversationId': 'Conversations',
                'turn_count': 'Messages utilisateur'
            }),
            hide_index=True
        )
        
        # Create visualizations
        st.subheader("📊 Évolution quotidienne")
        
        # Conversations histogram
        fig_conv = go.Figure()
        fig_conv.add_trace(
            go.Bar(
                x=daily_data['date_formatted'],
                y=daily_data['conversationId'],
                name="Conversations"
            )
        )
        fig_conv.update_layout(
            title="Évolution des conversations",
            xaxis_title="",
            yaxis_title="Nombre de conversations",
            height=400,
            showlegend=False
        )
        st.plotly_chart(fig_conv, use_container_width=True)
        
        # Messages histogram
        fig_msg = go.Figure()
        fig_msg.add_trace(
            go.Bar(
                x=daily_data['date_formatted'],
                y=daily_data['turn_count'],
                name="Messages utilisateur"
            )
        )
        fig_msg.update_layout(
            title="Évolution des messages utilisateur",
            xaxis_title="",
            yaxis_title="Nombre de messages",
            height=400,
            showlegend=False
        )
        st.plotly_chart(fig_msg, use_container_width=True)
        
    except Exception as e:
        st.info("Une erreur est survenue lors de l'affichage des métriques de conversation.")

def count_default_phrases(text: str, phrases: List[str]) -> int:
    """Count occurrences of exact phrases in text"""
    count = 0
    for phrase in phrases:
        # Count exact matches of the phrase
        count += text.lower().count(phrase.lower())
    return count

def analyze_formulaires(text: str, formulaires: List[Dict]) -> Dict:
    """Analyze form triggers and completions in text"""
    results = {}
    for formulaire in formulaires:
        name = formulaire['name']
        start = formulaire['start_phrase'].lower()
        end = formulaire['end_phrase'].lower()
        
        # Count triggers
        triggers = text.lower().count(start)
        
        # Count completions
        # Only count completions that occur after a trigger
        completions = 0
        text_lower = text.lower()
        last_pos = 0
        
        while True:
            start_pos = text_lower.find(start, last_pos)
            if start_pos == -1:
                break
                
            end_pos = text_lower.find(end, start_pos + len(start))
            if end_pos != -1:
                completions += 1
                
            last_pos = start_pos + 1
        
        results[name] = {
            'triggers': triggers,
            'completions': completions
        }
    
    return results

def display_default_stats(df: pd.DataFrame):
    """Display statistics for default phrases"""
    if df.empty or 'default_count' not in df.columns:
        st.info("🤖 Aucune donnée disponible pour les statistiques des réponses par défaut.")
        return
        
    try:
        st.subheader("🤖 Statistiques des réponses par défaut")
        
        total_defaults = df['default_count'].sum()
        if total_defaults == 0:
            st.info("Aucune réponse par défaut n'a été détectée.")
            return
            
        conversations_with_defaults = len(df[df['default_count'] > 0])
        total_conversations = len(df)
        default_rate = (conversations_with_defaults / total_conversations * 100)
        avg_defaults = df['default_count'].mean()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total des réponses par défaut", total_defaults)
        col2.metric("Taux de réponses par défaut", f"{default_rate:.1f}%", 
                    help="Pourcentage de conversations contenant au moins une réponse par défaut")
        col3.metric("Moyenne par conversation", f"{avg_defaults:.2f}")
        
        # Theme correlation with sous-themes
        if 'theme_principal' in df.columns and 'sous_theme' in df.columns:
            # Group by both theme and sous-theme
            theme_defaults = df[df['default_count'] > 0].groupby(
                ['theme_principal', 'sous_theme']
            ).agg({
                'default_count': ['count', 'sum']
            }).reset_index()
            
            if theme_defaults.empty:
                return
            
            # Rename columns for clarity
            theme_defaults.columns = [
                'theme_principal',
                'sous_theme',
                'conversations',
                'total_defaults'
            ]
            
            # Sort by total defaults descending
            theme_defaults = theme_defaults.sort_values(
                'total_defaults',
                ascending=False
            )
            
            # Calculate percentages
            theme_defaults['pourcentage'] = (
                theme_defaults['total_defaults'] / total_defaults * 100
            ).round(1)
            
            # Format the display
            st.subheader("📊 Répartition par thème et sous-thème")
            st.dataframe(
                theme_defaults,
                column_config={
                    "theme_principal": st.column_config.TextColumn(
                        "Thème principal",
                        width="medium"
                    ),
                    "sous_theme": st.column_config.TextColumn(
                        "Sous-thème",
                        width="medium"
                    ),
                    "conversations": st.column_config.NumberColumn(
                        "Nombre de conversations",
                        help="Nombre de conversations contenant des réponses par défaut"
                    ),
                    "total_defaults": st.column_config.NumberColumn(
                        "Total des réponses",
                        help="Nombre total de réponses par défaut"
                    ),
                    "pourcentage": st.column_config.NumberColumn(
                        "Pourcentage",
                        help="Pourcentage du total des réponses par défaut",
                        format="%.1f%%"
                    )
                },
                hide_index=True
            )
            
    except Exception as e:
        st.info("Une erreur est survenue lors de l'affichage des statistiques des réponses par défaut.")

def display_formulaire_stats(df: pd.DataFrame):
    """Display statistics for forms"""
    if df.empty or 'formulaire_data' not in df.columns:
        st.info("📝 Aucune donnée disponible pour les statistiques des formulaires.")
        return
        
    try:
        st.subheader("📝 Statistiques des formulaires")
        
        # Extract form data
        formulaire_data = []
        for idx, row in df.iterrows():
            if row['formulaire_data']:
                data = json.loads(row['formulaire_data'])
                for formulaire_name, stats in data.items():
                    formulaire_data.append({
                        'name': formulaire_name,
                        'triggers': stats['triggers'],
                        'completions': stats['completions']
                    })
        
        if not formulaire_data:
            st.info("Aucun formulaire n'a été utilisé.")
            return
            
        formulaire_df = pd.DataFrame(formulaire_data)
        formulaire_summary = formulaire_df.groupby('name').agg({
            'triggers': 'sum',
            'completions': 'sum'
        }).reset_index()
        
        formulaire_summary['completion_rate'] = (
            formulaire_summary['completions'] / 
            formulaire_summary['triggers']
        ).fillna(0)
        
        st.dataframe(
            formulaire_summary.assign(
                completion_rate=lambda x: x['completion_rate'].map('{:.1%}'.format)
            )
        )
        
        # Global stats
        total_triggers = formulaire_summary['triggers'].sum()
        total_completions = formulaire_summary['completions'].sum()
        global_completion_rate = (
            total_completions / total_triggers if total_triggers > 0 else 0
        )
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total des déclenchements", total_triggers)
        col2.metric("Total des complétions", total_completions)
        col3.metric("Taux de complétion global", f"{global_completion_rate:.1%}")
            
    except Exception as e:
        st.info("Une erreur est survenue lors de l'affichage des statistiques des formulaires.")

def display_satisfaction_metrics(df: pd.DataFrame):
    """Display satisfaction metrics including feedback rates and top negative themes"""
    if df.empty:
        st.info("😊 Aucune donnée disponible pour les métriques de satisfaction.")
        return
        
    required_columns = ['feedbackPositive', 'feedbackNegative']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.info(f"😊 Certaines colonnes de feedback ne sont pas disponibles : {', '.join(missing_columns)}")
        return
    
    try:
        st.subheader("😊 Métriques de satisfaction")
        
        # Calculate basic metrics
        total_conversations = len(df)
        total_negative = df['feedbackNegative'].sum()
        total_positive = df['feedbackPositive'].sum()
        total_votes = total_negative + total_positive
        
        if total_votes == 0:
            st.info("Aucun feedback n'a été enregistré.")
            return
        
        # Calculate negative feedback rate
        negative_rate = (total_negative / total_conversations * 100) if total_conversations > 0 else 0
        
        # Display main metrics
        col1, col2, col3 = st.columns(3)
        col1.metric(
            "Taux de feedback négatif",
            f"{negative_rate:.1f}%",
            help="Nombre total de feedback négatifs divisé par le nombre total de conversations"
        )
        col2.metric(
            "Votes totaux",
            total_votes,
            help="Nombre total de votes (positifs + négatifs)"
        )
        col3.metric(
            "Répartition des votes",
            f"👍 {total_positive} / 👎 {total_negative}",
            help="Nombre de votes positifs / nombre de votes négatifs"
        )
        
        # Calculate themes with negative feedback
        if 'sous_theme' in df.columns:
            st.subheader("🔍 Sous-thèmes avec feedback négatif")
            
            theme_feedback = df.groupby('sous_theme').agg({
                'feedbackNegative': 'sum',
                'feedbackPositive': 'sum'
            }).reset_index()
            
            # Filter to keep only themes with negative feedback
            theme_feedback = theme_feedback[theme_feedback['feedbackNegative'] > 0]
            
            if theme_feedback.empty:
                st.info("Aucun sous-thème n'a reçu de feedback négatif.")
            else:
                # Sort by negative feedback
                theme_feedback = theme_feedback.sort_values('feedbackNegative', ascending=False)
                
                # Calculate percentages
                theme_feedback['total_feedback'] = theme_feedback['feedbackPositive'] + theme_feedback['feedbackNegative']
                theme_feedback['negative_rate'] = (theme_feedback['feedbackNegative'] / theme_feedback['total_feedback'] * 100).round(1)
                
                # Display as table
                st.dataframe(
                    theme_feedback.assign(
                        negative_rate=lambda x: x['negative_rate'].map('{:.1f}%'.format)
                    ).rename(columns={
                        'sous_theme': 'Sous-thème',
                        'feedbackNegative': 'Feedback négatif',
                        'feedbackPositive': 'Feedback positif',
                        'total_feedback': 'Total feedback',
                        'negative_rate': 'Taux négatif'
                    }),
                    hide_index=True,
                    column_config={
                        "Sous-thème": st.column_config.TextColumn("Sous-thème", width="large"),
                        "Feedback négatif": st.column_config.NumberColumn("👎 Négatif"),
                        "Feedback positif": st.column_config.NumberColumn("👍 Positif"),
                        "Total feedback": st.column_config.NumberColumn("Total"),
                        "Taux négatif": st.column_config.TextColumn("% Négatif")
                    }
                )
                
                # Create bar chart
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=theme_feedback['sous_theme'],
                    y=theme_feedback['feedbackNegative'],
                    name='Feedback négatif',
                    marker_color='#ff6b6b'
                ))
                fig.add_trace(go.Bar(
                    x=theme_feedback['sous_theme'],
                    y=theme_feedback['feedbackPositive'],
                    name='Feedback positif',
                    marker_color='#51cf66'
                ))
                
                fig.update_layout(
                    title="Répartition des feedbacks par sous-thème",
                    xaxis_title="",
                    yaxis_title="Nombre de feedback",
                    barmode='group',
                    height=400,
                    showlegend=True
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            # Analyze positive feedback by sub-theme
            st.subheader("✨ Sous-thèmes avec feedback positif")
            
            theme_feedback_positive = df.groupby('sous_theme').agg({
                'feedbackPositive': 'sum',
                'feedbackNegative': 'sum'
            }).reset_index()
            
            # Filter to keep only themes with positive feedback
            theme_feedback_positive = theme_feedback_positive[theme_feedback_positive['feedbackPositive'] > 0]
            
            if theme_feedback_positive.empty:
                st.info("Aucun sous-thème n'a reçu de feedback positif.")
            else:
                # Sort by positive feedback
                theme_feedback_positive = theme_feedback_positive.sort_values('feedbackPositive', ascending=False)
                
                # Calculate percentages
                theme_feedback_positive['total_feedback'] = theme_feedback_positive['feedbackPositive'] + theme_feedback_positive['feedbackNegative']
                theme_feedback_positive['positive_rate'] = (theme_feedback_positive['feedbackPositive'] / theme_feedback_positive['total_feedback'] * 100).round(1)
                
                # Display as table
                st.dataframe(
                    theme_feedback_positive.assign(
                        positive_rate=lambda x: x['positive_rate'].map('{:.1f}%'.format)
                    ).rename(columns={
                        'sous_theme': 'Sous-thème',
                        'feedbackPositive': 'Feedback positif',
                        'feedbackNegative': 'Feedback négatif',
                        'total_feedback': 'Total feedback',
                        'positive_rate': 'Taux positif'
                    }),
                    hide_index=True,
                    column_config={
                        "Sous-thème": st.column_config.TextColumn("Sous-thème", width="large"),
                        "Feedback positif": st.column_config.NumberColumn("👍 Positif"),
                        "Feedback négatif": st.column_config.NumberColumn("👎 Négatif"),
                        "Total feedback": st.column_config.NumberColumn("Total"),
                        "Taux positif": st.column_config.TextColumn("% Positif")
                    }
                )
                
                # Create bar chart
                fig_positive = go.Figure()
                fig_positive.add_trace(go.Bar(
                    x=theme_feedback_positive['sous_theme'],
                    y=theme_feedback_positive['feedbackPositive'],
                    name='Feedback positif',
                    marker_color='#51cf66'
                ))
                fig_positive.add_trace(go.Bar(
                    x=theme_feedback_positive['sous_theme'],
                    y=theme_feedback_positive['feedbackNegative'],
                    name='Feedback négatif',
                    marker_color='#ff6b6b'
                ))
                
                fig_positive.update_layout(
                    title="Répartition des feedbacks par sous-thème (vue positive)",
                    xaxis_title="",
                    yaxis_title="Nombre de feedback",
                    barmode='group',
                    height=400,
                    showlegend=True
                )
                
                st.plotly_chart(fig_positive, use_container_width=True)
        
    except Exception as e:
        st.info("Une erreur est survenue lors de l'affichage des métriques de satisfaction.")

def display_hot_topic_stats(df: pd.DataFrame):
    """Display statistics for hot topics including distribution pie charts"""
    if df.empty or 'is_hot_topic' not in df.columns or 'hot_topic_name' not in df.columns:
        return
        
    try:
        st.subheader("🔥 Analyse des Hot Topics")
        
        # Calculate overall hot topic presence
        total_conversations = len(df)
        hot_topic_conversations = df['is_hot_topic'].sum()
        
        if hot_topic_conversations == 0:
            st.info("Aucun hot topic n'a été détecté.")
            return
            
        # Create columns for the two pie charts
        col1, col2 = st.columns(2)
        
        # First pie chart: Overall distribution
        with col1:
            fig1 = go.Figure(data=[go.Pie(
                labels=['Avec Hot Topic', 'Sans Hot Topic'],
                values=[hot_topic_conversations, total_conversations - hot_topic_conversations],
                hole=.3
            )])
            fig1.update_layout(
                title="Distribution des conversations avec Hot Topics",
                height=400
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        # Second pie chart: Hot topic names distribution
        with col2:
            hot_topic_counts = df[df['is_hot_topic']]['hot_topic_name'].value_counts()
            fig2 = go.Figure(data=[go.Pie(
                labels=hot_topic_counts.index,
                values=hot_topic_counts.values,
                hole=.3
            )])
            fig2.update_layout(
                title="Répartition des types de Hot Topics",
                height=400
            )
            st.plotly_chart(fig2, use_container_width=True)
            
        # Display summary metrics
        hot_topic_rate = (hot_topic_conversations / total_conversations * 100)
        st.metric(
            "Taux de conversations avec Hot Topic",
            f"{hot_topic_rate:.1f}%",
            help="Pourcentage de conversations contenant au moins un hot topic"
        )
        
        # Display detailed table of hot topic clicks
        st.markdown("### 📋 Détail des Hot Topics")
        
        hot_topic_counts = df[df['is_hot_topic']]['hot_topic_name'].value_counts()
        total_hot_topics = hot_topic_counts.sum()
        
        # Create DataFrame for the table
        hot_topic_table = pd.DataFrame({
            'Hot Topic': hot_topic_counts.index,
            'Nombre de clics': hot_topic_counts.values,
            '% des Hot Topics': (hot_topic_counts.values / total_hot_topics * 100).round(1),
            '% des conversations': (hot_topic_counts.values / total_conversations * 100).round(1)
        })
        
        # Add rank column
        hot_topic_table.insert(0, 'Rang', range(1, len(hot_topic_table) + 1))
        
        # Display the table
        st.dataframe(
            hot_topic_table.assign(
                **{
                    '% des Hot Topics': lambda x: x['% des Hot Topics'].map('{:.1f}%'.format),
                    '% des conversations': lambda x: x['% des conversations'].map('{:.1f}%'.format)
                }
            ),
            hide_index=True,
            column_config={
                "Rang": st.column_config.NumberColumn("Rang", width="small"),
                "Hot Topic": st.column_config.TextColumn("Hot Topic", width="large"),
                "Nombre de clics": st.column_config.NumberColumn("Clics", help="Nombre de fois où ce Hot Topic a été détecté"),
                "% des Hot Topics": st.column_config.TextColumn("% Hot Topics", help="Pourcentage par rapport au total des Hot Topics détectés"),
                "% des conversations": st.column_config.TextColumn("% Conversations", help="Pourcentage par rapport au total des conversations")
            }
        )
        
        # Add summary line
        st.caption(f"📊 Total : {total_hot_topics} Hot Topics détectés dans {hot_topic_conversations} conversations sur {total_conversations} conversations totales")
        
    except Exception as e:
        st.info("Une erreur est survenue lors de l'affichage des statistiques des hot topics.")

def display_language_analysis(df: pd.DataFrame):
    """Display language distribution and top sub-themes per language"""
    if df.empty:
        st.info("🌍 Aucune donnée disponible pour l'analyse des langues.")
        return
        
    try:
        st.subheader("🌍 Analyse par langue")
        
        # Check if language columns exist
        has_language = 'language_normalized' in df.columns
        
        if not has_language:
            st.info("Colonne 'language_normalized' non trouvée - cette analyse n'est pas disponible")
            return
        
        # Calculate language distribution (excluding empty values)
        language_data = df[df['language_normalized'].notna() & (df['language_normalized'] != '')]
        
        if language_data.empty:
            st.info("Aucune donnée de langue disponible")
            return
        
        # Global language distribution with grouping of languages <1%
        raw_language_counts = language_data['language_normalized'].value_counts()
        total_with_language = len(language_data)
        
        # Calculate percentages and identify languages <1%
        language_percentages = (raw_language_counts / total_with_language * 100)
        major_languages = language_percentages[language_percentages >= 1.0]
        minor_languages = language_percentages[language_percentages < 1.0]
        
        # Create final language counts with "Autres" category
        language_counts = major_languages.copy()
        if len(minor_languages) > 0:
            language_counts['Autres'] = minor_languages.sum()
        
        # Convert back to counts for display
        language_counts_display = (language_counts / 100 * total_with_language).round().astype(int)
        
        st.markdown("### 📊 Répartition globale des langues")
        
        # Create two columns for side-by-side display
        col1, col2 = st.columns([1, 1])
        
        # Left column: Pie chart
        with col1:
            # Create pie chart for language distribution
            fig_lang = go.Figure(data=[go.Pie(
                labels=language_counts_display.index,
                values=language_counts_display.values,
                hole=0.3
            )])
            
            fig_lang.update_layout(
                title="Distribution des langues",
                height=400,
                showlegend=True
            )
            
            st.plotly_chart(fig_lang, use_container_width=True)
        
        # Right column: Summary table
        with col2:
            st.markdown("#### 📋 Récapitulatif")
            
            # Language summary table
            lang_summary_df = pd.DataFrame({
                'Langue': language_counts_display.index,
                'Nombre de conversations': language_counts_display.values,
                'Pourcentage': language_counts.round(1)
            })
            
            st.dataframe(
                lang_summary_df.assign(
                    Pourcentage=lambda x: x['Pourcentage'].map('{:.1f}%'.format)
                ),
                hide_index=True,
                column_config={
                    "Langue": st.column_config.TextColumn("Langue", width="small"),
                    "Nombre de conversations": st.column_config.NumberColumn("Conversations"),
                    "Pourcentage": st.column_config.TextColumn("Pourcentage")
                },
                use_container_width=True
            )
        
        # Top sub-themes per language (only if theme data is available)
        if 'sous_theme' in df.columns:
            st.markdown("### 🎯 Top sous-thèmes par langue")
            
            # Get unique languages sorted by frequency (excluding "Autres")
            display_languages = [lang for lang in language_counts_display.index if lang != 'Autres']
            top_languages = display_languages[:6]  # Show top 6 languages max
            
            # Create columns for displaying multiple languages side by side
            cols_per_row = 2
            rows_needed = (len(top_languages) + cols_per_row - 1) // cols_per_row
            
            for row in range(rows_needed):
                cols = st.columns(cols_per_row)
                
                for col_idx in range(cols_per_row):
                    lang_idx = row * cols_per_row + col_idx
                    if lang_idx < len(top_languages):
                        language = top_languages[lang_idx]
                        
                        with cols[col_idx]:
                            st.markdown(f"#### 🏳️ {language}")
                            
                            # Filter data for this language
                            lang_df = language_data[language_data['language_normalized'] == language]
                            
                            # Get top sub-themes for this language
                            if not lang_df.empty and 'sous_theme' in lang_df.columns:
                                sous_theme_counts = lang_df['sous_theme'].value_counts().head(5)  # Top 5 sub-themes
                                
                                if not sous_theme_counts.empty:
                                    # Create DataFrame for display
                                    theme_df = pd.DataFrame({
                                        'Sous-thème': sous_theme_counts.index,
                                        'Occurrences': sous_theme_counts.values,
                                        'Pourcentage': (sous_theme_counts.values / len(lang_df) * 100).round(1)
                                    })
                                    
                                    # Add rank
                                    theme_df['Rang'] = range(1, len(theme_df) + 1)
                                    theme_df = theme_df[['Rang', 'Sous-thème', 'Occurrences', 'Pourcentage']]
                                    
                                    st.dataframe(
                                        theme_df.assign(
                                            Pourcentage=lambda x: x['Pourcentage'].map('{:.1f}%'.format)
                                        ),
                                        hide_index=True,
                                        column_config={
                                            "Rang": st.column_config.NumberColumn("#", width="small"),
                                            "Sous-thème": st.column_config.TextColumn("Sous-thème", width="large"),
                                            "Occurrences": st.column_config.NumberColumn("Nb"),
                                            "Pourcentage": st.column_config.TextColumn("%")
                                        }
                                    )
                                    
                                    # Show total conversations for this language
                                    st.caption(f"Total: {len(lang_df)} conversations en {language}")
                                else:
                                    st.info("Aucun sous-thème disponible")
                            else:
                                st.info("Données de thèmes non disponibles")
        else:
            st.info("Colonnes de thèmes non disponibles pour l'analyse détaillée par langue")
        
    except Exception as e:
        st.info("Une erreur est survenue lors de l'affichage de l'analyse des langues.")

def display_url_and_device_stats(df: pd.DataFrame):
    """Display URL frequency analysis and device distribution"""
    if df.empty:
        st.info("🔗 Aucune donnée disponible pour l'analyse des URLs et appareils.")
        return
        
    try:
        st.subheader("🔗 Analyse des URLs et appareils")
        
        # Check if required columns exist
        has_urls = 'urls' in df.columns
        has_device = 'device' in df.columns
        
        if not has_urls and not has_device:
            st.info("Colonnes 'urls' et 'device' non trouvées - cette analyse n'est pas disponible")
            return
        
        # Create two columns for side-by-side display
        col1, col2 = st.columns(2)
        
        # URLs Analysis
        if has_urls:
            with col1:
                st.markdown("### 🔗 Top 10 des URLs les plus fréquentes")
                
                # Extract and count URLs
                url_counts = {}
                
                for idx, row in df.iterrows():
                    urls_cell = row['urls']
                    if pd.notna(urls_cell) and urls_cell:
                        # Split URLs by comma and clean them
                        urls = [url.strip() for url in str(urls_cell).split(',') if url.strip()]
                        
                        for url in urls:
                            url_counts[url] = url_counts.get(url, 0) + 1
                
                if url_counts:
                    # Convert to sorted list and get top 10
                    top_urls = sorted(url_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                    
                    # Create DataFrame for display
                    url_df = pd.DataFrame(top_urls, columns=['URL', 'Nombre d\'occurrences'])
                    url_df['Rang'] = range(1, len(url_df) + 1)
                    
                    # Reorder columns
                    url_df = url_df[['Rang', 'URL', 'Nombre d\'occurrences']]
                    
                    st.dataframe(
                        url_df,
                        hide_index=True,
                        column_config={
                            "Rang": st.column_config.NumberColumn("Rang", width="small"),
                            "URL": st.column_config.TextColumn("URL", width="large"),
                            "Nombre d'occurrences": st.column_config.NumberColumn("Occurrences")
                        }
                    )
                    
                    # Display total stats
                    total_urls = sum(url_counts.values())
                    unique_urls = len(url_counts)
                    
                    st.metric("Total URLs trouvées", total_urls)
                    st.metric("URLs uniques", unique_urls)
                else:
                    st.info("Aucune URL trouvée dans les données")
        else:
            with col1:
                st.info("Colonne 'urls' non trouvée")
        
        # Device Analysis
        if has_device:
            with col2:
                st.markdown("### 📱 Répartition des appareils")
                
                # Count devices
                device_counts = df['device'].value_counts()
                
                if not device_counts.empty:
                    # Create pie chart
                    fig = go.Figure(data=[go.Pie(
                        labels=device_counts.index,
                        values=device_counts.values,
                        hole=0.3
                    )])
                    
                    fig.update_layout(
                        title="Distribution des types d'appareils",
                        height=400,
                        showlegend=True
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Display device stats
                    st.markdown("#### 📊 Détail par appareil")
                    device_df = pd.DataFrame({
                        'Appareil': device_counts.index,
                        'Nombre': device_counts.values,
                        'Pourcentage': (device_counts.values / device_counts.sum() * 100).round(1)
                    })
                    
                    st.dataframe(
                        device_df.assign(
                            Pourcentage=lambda x: x['Pourcentage'].map('{:.1f}%'.format)
                        ),
                        hide_index=True,
                        column_config={
                            "Appareil": st.column_config.TextColumn("Type d'appareil"),
                            "Nombre": st.column_config.NumberColumn("Nombre de conversations"),
                            "Pourcentage": st.column_config.TextColumn("Pourcentage")
                        }
                    )
                else:
                    st.info("Aucune donnée d'appareil trouvée")
        else:
            with col2:
                st.info("Colonne 'device' non trouvée")
        
    except Exception as e:
        st.info("Une erreur est survenue lors de l'affichage des statistiques URL/Device.")

def main():
    st.set_page_config(page_title="scuuba light - Client Dashboard", layout="wide")
    
    st.title("✨ scuuba light - Dashboard Client")
    st.write("Téléchargez votre fichier d'analyse pour visualiser les résultats.")
    
    uploaded_file = st.file_uploader("Choisissez un fichier CSV d'analyse", type="csv")
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            
            if not is_processed_file(df):
                st.error("Le fichier ne contient pas toutes les colonnes requises. Assurez-vous d'utiliser un fichier d'analyse complet généré par Genii Insights.")
                st.info("Colonnes requises: theme_principal, sous_theme, date, conversationId, turn_count, default_count, feedbackPositive, feedbackNegative")
                return
            
            # Data validation and preparation
            df['date'] = pd.to_datetime(df['date'], format='ISO8601').dt.normalize()
            
            # Show file info
            st.success("✅ Fichier d'analyse valide")
            st.info(f"📊 {len(df)} conversations analysées")
            
            # Date range picker for filtering
            st.markdown("### 📅 Filtrer par période")
            
            # Get date range from data
            min_date = df['date'].min().date()
            max_date = df['date'].max().date()
            
            # Create date range picker
            date_range = st.date_input(
                "Sélectionnez la période à analyser:",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                help=f"Données disponibles du {min_date.strftime('%d/%m/%Y')} au {max_date.strftime('%d/%m/%Y')}"
            )
            
            # Filter DataFrame based on selected date range
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start_date, end_date = date_range
                df_filtered = df[(df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)]
                st.info(f"🔍 {len(df_filtered)} conversations dans la période sélectionnée (sur {len(df)} conversations au total)")
            else:
                # If only one date selected or invalid range, use all data
                df_filtered = df
                st.info("⚠️ Veuillez sélectionner une période complète (date de début et de fin)")
            
            # Display all statistics
            st.markdown("### 📊 Tableau de bord")
            
            # Display metrics in order of importance
            with st.spinner("Génération des métriques de satisfaction..."):
                display_satisfaction_metrics(df_filtered)
            
            with st.spinner("Génération des métriques de conversation..."):
                display_conversation_metrics(df_filtered)
            
            # Display URL and device statistics
            with st.spinner("Génération des statistiques URLs et appareils..."):
                display_url_and_device_stats(df_filtered)
            
            # Display language analysis
            with st.spinner("Génération de l'analyse des langues..."):
                display_language_analysis(df_filtered)
            
            with st.spinner("Génération des statistiques des thèmes..."):
                display_statistics(df_filtered)
            
            # Only display hot topic stats if the required columns exist
            if 'is_hot_topic' in df_filtered.columns and 'hot_topic_name' in df_filtered.columns:
                with st.spinner("Génération des statistiques des hot topics..."):
                    display_hot_topic_stats(df_filtered)
            
            if 'default_count' in df_filtered.columns:
                with st.spinner("Génération des statistiques des réponses par défaut..."):
                    display_default_stats(df_filtered)
            
            if 'formulaire_data' in df_filtered.columns:
                with st.spinner("Génération des statistiques des formulaires..."):
                    display_formulaire_stats(df_filtered)

        except Exception as e:
            st.error(f"Erreur lors du traitement : {str(e)}")
            st.error("Détails de l'erreur pour le support technique:")
            st.code(str(e))

if __name__ == "__main__":
    main() 