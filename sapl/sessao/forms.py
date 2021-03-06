from datetime import datetime

import django_filters
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Button, Fieldset, Layout
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.forms import ModelForm
from django.utils.translation import ugettext_lazy as _

from sapl.base.models import Autor, TipoAutor
from sapl.crispy_layout_mixin import form_actions, to_row
from sapl.materia.forms import MateriaLegislativaFilterSet
from sapl.materia.models import (MateriaLegislativa, StatusTramitacao,
                                 TipoMateriaLegislativa)
from sapl.parlamentares.models import Parlamentar, Legislatura, Mandato
from sapl.utils import (RANGE_DIAS_MES, RANGE_MESES,
                        MateriaPesquisaOrderingFilter, autor_label,
                        autor_modal, timezone)

from .models import (Bancada, Bloco, ExpedienteMateria, Orador,
                     OradorExpediente, OrdemDia, SessaoPlenaria,
                     SessaoPlenariaPresenca, TipoResultadoVotacao)


def recupera_anos():
    try:
        anos_list = SessaoPlenaria.objects.all().dates('data_inicio', 'year')
        # a listagem deve ser em ordem descrescente, mas por algum motivo
        # a adicao de .order_by acima depois do all() nao surte efeito
        # apos a adicao do .dates(), por isso o reversed() abaixo
        anos = [(k.year, k.year) for k in reversed(anos_list)]
        return anos
    except Exception:
        return []


def ANO_CHOICES():
    return [('', '---------')] + recupera_anos()


MES_CHOICES = [('', '---------')] + RANGE_MESES
DIA_CHOICES = [('', '---------')] + RANGE_DIAS_MES


ORDENACAO_RESUMO = [('cont_mult', 'Conteúdo Multimídia'),
                    ('exp', 'Expedientes'),
                    ('id_basica', 'Identificação Básica'),
                    ('lista_p', 'Lista de Presença'),
                    ('lista_p_o_d', 'Lista de Presença Ordem do Dia'),
                    ('mat_exp', 'Matérias do Expediente'),
                    ('mat_o_d', 'Matérias da Ordem do Dia'),
                    ('mesa_d', 'Mesa Diretora'),
                    ('oradores_exped', 'Oradores do Expediente'),
                    ('oradores_expli', 'Oradores das Explicações Pessoais')]


class SessaoPlenariaForm(ModelForm):

    class Meta:
        model = SessaoPlenaria
        exclude = ['cod_andamento_sessao']

    def clean(self):
        super(SessaoPlenariaForm, self).clean()

        if not self.is_valid():
            return self.cleaned_data

        instance = self.instance

        num = self.cleaned_data['numero']
        sl = self.cleaned_data['sessao_legislativa']
        leg = self.cleaned_data['legislatura']
        tipo = self.cleaned_data['tipo']
        abertura = self.cleaned_data['data_inicio']
        encerramento = self.cleaned_data['data_fim']

        error = ValidationError(
            "Número de Sessão Plenária já existente "
            "para a Legislatura, Sessão Legislativa e Tipo informados. "
            "Favor escolher um número distinto.")

        sessoes = SessaoPlenaria.objects.filter(numero=num,
                                                sessao_legislativa=sl,
                                                legislatura=leg,
                                                tipo=tipo).\
            values_list('id', flat=True)

        qtd_sessoes = len(sessoes)

        if qtd_sessoes > 0:
            if instance.pk:  # update
                if instance.pk not in sessoes or qtd_sessoes > 1:
                    raise error
            else:  # create
                raise error


        # Condições da verificação
        abertura_entre_leg = leg.data_inicio <= abertura <= leg.data_fim
        abertura_entre_sl = sl.data_inicio <= abertura <= sl.data_fim
        if encerramento is not None:
            encerramento_entre_leg = leg.data_inicio <= encerramento <= leg.data_fim
            encerramento_entre_sl = sl.data_inicio <= encerramento <= sl.data_fim
        # Verificação das datas de abertura e encerramento da Sessão
        # Verificações com a data de encerramento preenchidas
        if encerramento is not None:
            # Verifica se a data de encerramento é anterior a data de abertura
            if encerramento < abertura:
                raise ValidationError("A data de encerramento não pode ser "
                                      "anterior a data de abertura.")
            # Verifica se a data de abertura está entre a data de início e fim da legislatura
            if abertura_entre_leg and encerramento_entre_leg:
                if abertura_entre_sl and encerramento_entre_sl:
                    pass
                elif abertura_entre_sl and not encerramento_entre_sl:
                    raise ValidationError("A data de encerramento deve estar entre "
                                          "as datas de início e fim da Sessão Legislativa.")
                elif not abertura_entre_sl and encerramento_entre_sl:
                    raise ValidationError("A data de abertura deve estar entre as "
                                          "datas de início e fim da Sessão Legislativa.")
                elif not abertura_entre_sl and not encerramento_entre_sl:
                    raise ValidationError("A data de abertura e de encerramento devem estar "
                                          "entre as datas de início e fim da Sessão Legislativa.")
            elif abertura_entre_leg and not encerramento_entre_leg:
                if abertura_entre_sl and encerramento_entre_sl:
                    raise ValidationError("A data de encerramento deve estar entre "
                                          "as datas de início e fim da Legislatura.")
                elif abertura_entre_sl and not encerramento_entre_sl:
                    raise ValidationError("A data de encerramento deve estar entre "
                                          "as datas de início e fim tanto da "
                                          "Legislatura quanto da Sessão Legislativa.")
                elif not abertura_entre_sl and encerramento_entre_sl:
                    raise ValidationError("As datas de abertura e encerramento devem "
                                          "estar entre as "
                                          "datas de início e fim tanto Legislatura "
                                          "quanto da Sessão Legislativa.")
                elif not abertura_entre_sl and not encerramento_entre_sl:
                    raise ValidationError("As datas de abertura e encerramento devem "
                                          "estar entre as "
                                          "datas de início e fim tanto Legislatura "
                                          "quanto da Sessão Legislativa.")
            elif not abertura_entre_leg and not encerramento_entre_leg:
                if abertura_entre_sl and encerramento_entre_sl:
                    raise ValidationError("As datas de abertura e encerramento devem "
                                          "estar entre as "
                                          "datas de início e fim da Legislatura.")
                elif abertura_entre_sl and not encerramento_entre_sl:
                    raise ValidationError("As datas de abertura e encerramento devem "
                                          "estar entre as "
                                          "datas de início e fim tanto Legislatura "
                                          "quanto da Sessão Legislativa.")
                elif not abertura_entre_sl and encerramento_entre_sl:
                    raise ValidationError("As datas de abertura e encerramento devem "
                                          "estar entre as "
                                          "datas de início e fim tanto Legislatura "
                                          "quanto da Sessão Legislativa.")
                elif not abertura_entre_sl and not encerramento_entre_sl:
                    raise ValidationError("As datas de abertura e encerramento devem "
                                          "estar entre as "
                                          "datas de início e fim tanto Legislatura "
                                          "quanto da Sessão Legislativa.")


        # Verificações com a data de encerramento vazia
        else:
            if abertura_entre_leg:
                if abertura_entre_sl:
                    pass
                else:
                    raise ValidationError("A data de abertura da sessão deve estar "
                                          "entre a data de início e fim da Sessão Legislativa.")
            else:
                if abertura_entre_sl:
                    raise ValidationError("A data de abertura da sessão deve estar "
                                          "entre a data de início e fim da Legislatura.")
                else:
                    raise ValidationError("A data de abertura da sessão deve estar "
                                          "entre a data de início e fim tanto da "
                                          "Legislatura quanto da Sessão Legislativa.")

        return self.cleaned_data


class BancadaForm(ModelForm):

    class Meta:
        model = Bancada
        fields = ['legislatura', 'nome', 'partido', 'data_criacao',
                  'data_extincao', 'descricao']

    def clean(self):
        super(BancadaForm, self).clean()

        if not self.is_valid():
            return self.cleaned_data

        data = self.cleaned_data

        legislatura = data['legislatura']

        data_criacao = data['data_criacao']
        if data_criacao:
            if (data_criacao < legislatura.data_inicio or
                    data_criacao > legislatura.data_fim):
                raise ValidationError(_("Data de criação da bancada fora do intervalo"
                                        " de legislatura informada"))

        data_extincao = data['data_extincao']
        if data_extincao:
            if (data_extincao < legislatura.data_inicio or
                    data_extincao > legislatura.data_fim):
                raise ValidationError(_("Data fim da bancada fora do intervalo de"
                                        " legislatura informada"))

        if self.cleaned_data['data_extincao']:
            if (self.cleaned_data['data_extincao'] <
                    self.cleaned_data['data_criacao']):
                msg = _('Data de extinção não pode ser menor que a de criação')
                raise ValidationError(msg)
        return self.cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        bancada = super(BancadaForm, self).save(commit)
        content_type = ContentType.objects.get_for_model(Bancada)
        object_id = bancada.pk
        tipo = TipoAutor.objects.get(descricao__icontains='Bancada')
        Autor.objects.create(
            content_type=content_type,
            object_id=object_id,
            tipo=tipo,
            nome=bancada.nome
        )
        return bancada


class BlocoForm(ModelForm):

    class Meta:
        model = Bloco
        fields = ['nome', 'partidos', 'data_criacao',
                  'data_extincao', 'descricao']

    def clean(self):
        super(BlocoForm, self).clean()

        if not self.is_valid():
            return self.cleaned_data

        if self.cleaned_data['data_extincao']:
            if (self.cleaned_data['data_extincao'] <
                    self.cleaned_data['data_criacao']):
                msg = _('Data de extinção não pode ser menor que a de criação')
                raise ValidationError(msg)
        return self.cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        bloco = super(BlocoForm, self).save(commit)
        content_type = ContentType.objects.get_for_model(Bloco)
        object_id = bloco.pk
        tipo = TipoAutor.objects.get(descricao__icontains='Bloco')
        Autor.objects.create(
            content_type=content_type,
            object_id=object_id,
            tipo=tipo,
            nome=bloco.nome
        )
        return bloco


class ExpedienteMateriaForm(ModelForm):

    _model = ExpedienteMateria
    data_atual = timezone.now()

    tipo_materia = forms.ModelChoiceField(
        label=_('Tipo Matéria'),
        required=True,
        queryset=TipoMateriaLegislativa.objects.all(),
        empty_label='Selecione',
        widget=forms.Select(attrs={'autocomplete': 'off'}))

    numero_materia = forms.CharField(
        label='Número Matéria', required=True,
        widget=forms.TextInput(attrs={'autocomplete': 'off'}))

    ano_materia = forms.CharField(
        label='Ano Matéria',
        initial=int(data_atual.year),
        required=True,
        widget=forms.TextInput(attrs={'autocomplete': 'off'}))

    data_ordem = forms.CharField(
        label='Data Sessão',
        initial=datetime.strftime(timezone.now(), '%d/%m/%Y'),
        widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    class Meta:
        model = ExpedienteMateria
        fields = ['data_ordem', 'numero_ordem', 'tipo_materia', 'observacao',
                  'numero_materia', 'ano_materia', 'tipo_votacao']

    def clean_numero_ordem(self):
        sessao = self.instance.sessao_plenaria

        numero_ordem_exists = ExpedienteMateria.objects.filter(
            sessao_plenaria=sessao,
            numero_ordem=self.cleaned_data['numero_ordem']).exists()

        if numero_ordem_exists and not self.instance.pk:
            msg = _('Esse número de ordem já existe.')
            raise ValidationError(msg)

        return self.cleaned_data['numero_ordem']

    def clean_data_ordem(self):
        return self.instance.sessao_plenaria.data_inicio

    def clean(self):
        cleaned_data = super(ExpedienteMateriaForm, self).clean()
        if not self.is_valid():
            return cleaned_data

        sessao = self.instance.sessao_plenaria

        try:
            materia = MateriaLegislativa.objects.get(
                numero=self.cleaned_data['numero_materia'],
                ano=self.cleaned_data['ano_materia'],
                tipo=self.cleaned_data['tipo_materia'])
        except ObjectDoesNotExist:
            msg = _('A matéria a ser inclusa não existe no cadastro'
                    ' de matérias legislativas.')
            raise ValidationError(msg)
        else:
            cleaned_data['materia'] = materia

        exists = self._model.objects.filter(
            sessao_plenaria=sessao,
            materia=materia).exists()

        if exists and not self.instance.pk:
            msg = _('Essa matéria já foi cadastrada.')
            raise ValidationError(msg)

        return cleaned_data

    def save(self, commit=False):
        expediente = super(ExpedienteMateriaForm, self).save(commit)
        expediente.materia = self.cleaned_data['materia']
        expediente.save()
        return expediente


class OrdemDiaForm(ExpedienteMateriaForm):

    _model = OrdemDia

    class Meta:
        model = OrdemDia
        fields = ['data_ordem', 'numero_ordem', 'tipo_materia', 'observacao',
                  'numero_materia', 'ano_materia', 'tipo_votacao']

    def clean_data_ordem(self):
        return self.instance.sessao_plenaria.data_inicio

    def clean_numero_ordem(self):
        sessao = self.instance.sessao_plenaria

        numero_ordem_exists = OrdemDia.objects.filter(
            sessao_plenaria=sessao,
            numero_ordem=self.cleaned_data['numero_ordem']).exists()

        if numero_ordem_exists and not self.instance.pk:
            msg = _('Esse número de ordem já existe.')
            raise ValidationError(msg)

        return self.cleaned_data['numero_ordem']

    def clean(self):
        cleaned_data = super(OrdemDiaForm, self).clean()
        if not self.is_valid():
            return cleaned_data
        return self.cleaned_data

    def save(self, commit=False):
        ordem = super(OrdemDiaForm, self).save(commit)
        ordem.materia = self.cleaned_data['materia']
        ordem.save()
        return ordem


class PresencaForm(forms.Form):
    presenca = forms.CharField(required=False, initial=False)
    parlamentar = forms.CharField(required=False, max_length=20)


class ListMateriaForm(forms.Form):
    error_message = forms.CharField(required=False, label='votacao_aberta')


class MesaForm(forms.Form):
    parlamentar = forms.IntegerField(required=True)
    cargo = forms.IntegerField(required=True)


class ExpedienteForm(forms.Form):
    conteudo = forms.CharField(required=False, widget=forms.Textarea)


class VotacaoForm(forms.Form):
    votos_sim = forms.CharField(label='Sim')
    votos_nao = forms.CharField(label='Não')
    abstencoes = forms.CharField(label='Abstenções')
    total_votos = forms.CharField(required=False, label='total')
    resultado_votacao = forms.CharField(label='Resultado da Votação')


class VotacaoNominalForm(forms.Form):
    resultado_votacao = forms.ModelChoiceField(label='Resultado da Votação',
                                               required=True,
                                               queryset=TipoResultadoVotacao.objects.all())


class VotacaoEditForm(forms.Form):
    pass


class SessaoPlenariaFilterSet(django_filters.FilterSet):

    data_inicio__year = django_filters.ChoiceFilter(required=False,
                                                    label='Ano',
                                                    choices=ANO_CHOICES)
    data_inicio__month = django_filters.ChoiceFilter(required=False,
                                                     label='Mês',
                                                     choices=MES_CHOICES)
    data_inicio__day = django_filters.ChoiceFilter(required=False,
                                                   label='Dia',
                                                   choices=DIA_CHOICES)
    titulo = _('Pesquisa de Sessão Plenária')

    class Meta:
        model = SessaoPlenaria
        fields = ['tipo']

    def __init__(self, *args, **kwargs):
        super(SessaoPlenariaFilterSet, self).__init__(*args, **kwargs)

        # pré-popula o campo do formulário com o ano corrente
        self.form.fields['data_inicio__year'].initial = timezone.now().year


        row1 = to_row(
            [('data_inicio__year', 3),
             ('data_inicio__month', 3),
             ('data_inicio__day', 3),
             ('tipo', 3)])

        self.form.helper = FormHelper()
        self.form.helper.form_method = 'GET'
        self.form.helper.layout = Layout(
            Fieldset(self.titulo,
                     row1,
                     form_actions(label='Pesquisar'))
        )


class AdicionarVariasMateriasFilterSet(MateriaLegislativaFilterSet):

    o = MateriaPesquisaOrderingFilter()
    tramitacao__status = django_filters.ModelChoiceFilter(
        required=True,
        queryset=StatusTramitacao.objects.all(),
        label=_('Status da Matéria'))

    class Meta:
        model = MateriaLegislativa
        fields = ['tramitacao__status',
                  'numero',
                  'numero_protocolo',
                  'ano',
                  'tipo',
                  'data_apresentacao',
                  'data_publicacao',
                  'autoria__autor__tipo',
                  # FIXME 'autoria__autor__partido',
                  'relatoria__parlamentar_id',
                  'local_origem_externa',
                  'em_tramitacao',
                  ]

    def __init__(self, *args, **kwargs):
        super(MateriaLegislativaFilterSet, self).__init__(*args, **kwargs)

        self.filters['tipo'].label = 'Tipo de Matéria'
        self.filters['autoria__autor__tipo'].label = 'Tipo de Autor'
        # self.filters['autoria__autor__partido'].label = 'Partido do Autor'
        self.filters['relatoria__parlamentar_id'].label = 'Relatoria'

        row1 = to_row(
            [('tramitacao__status', 12)])
        row2 = to_row(
            [('tipo', 12)])
        row3 = to_row(
            [('numero', 4),
             ('ano', 4),
             ('numero_protocolo', 4)])
        row4 = to_row(
            [('data_apresentacao', 6),
             ('data_publicacao', 6)])
        row5 = to_row(
            [('autoria__autor', 0),
             (Button('pesquisar',
                     'Pesquisar Autor',
                     css_class='btn btn-primary btn-sm'), 2),
             (Button('limpar',
                     'limpar Autor',
                     css_class='btn btn-primary btn-sm'), 10)])
        row6 = to_row(
            [('autoria__autor__tipo', 6),
             # ('autoria__autor__partido', 6)
             ])
        row7 = to_row(
            [('relatoria__parlamentar_id', 6),
             ('local_origem_externa', 6)])
        row8 = to_row(
            [('em_tramitacao', 6),
             ('o', 6)])
        row9 = to_row(
            [('ementa', 12)])

        self.form.helper = FormHelper()
        self.form.helper.form_method = 'GET'
        self.form.helper.layout = Layout(
            Fieldset(_('Pesquisa de Matéria'),
                     row1, row2, row3,
                     HTML(autor_label),
                     HTML(autor_modal),
                     row4, row5, row6, row7, row8, row9,
                     form_actions(label='Pesquisar'))
        )


class OradorForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(OradorForm, self).__init__(*args, **kwargs)

        id_sessao = int(self.initial['id_sessao'])

        ids = [s.parlamentar.id for
               s in SessaoPlenariaPresenca.objects.filter(
                   sessao_plenaria_id=id_sessao)]

        self.fields['parlamentar'].queryset = Parlamentar.objects.filter(
            id__in=ids).order_by('nome_parlamentar')

    class Meta:
        model = Orador
        exclude = ['sessao_plenaria']


class OradorExpedienteForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(OradorExpedienteForm, self).__init__(*args, **kwargs)
        legislatura_vigente = SessaoPlenaria.objects.get(pk=kwargs['initial']['id_sessao']).legislatura

        if legislatura_vigente:
            self.fields['parlamentar'].queryset = \
                Parlamentar.objects.filter(ativo=True,
                                           mandato__legislatura=legislatura_vigente
                                          ).order_by('nome_parlamentar')

    def clean(self):
        super(OradorExpedienteForm, self).clean()
        cleaned_data = self.cleaned_data

        if not self.is_valid():
            return self.cleaned_data

        sessao_id = self.initial['id_sessao']
        numero = self.initial.get('numero') # Retorna None se inexistente
        ordem = OradorExpediente.objects.filter(
                            sessao_plenaria_id=sessao_id,
                            numero_ordem=cleaned_data['numero_ordem']
                            ).exists()

        if ordem and (cleaned_data['numero_ordem'] != numero):
            raise ValidationError(_(
                'Já existe orador nesta posição da ordem de pronunciamento'))

        return self.cleaned_data


    class Meta:
        model = OradorExpediente
        exclude = ['sessao_plenaria']


class PautaSessaoFilterSet(SessaoPlenariaFilterSet):
    titulo = _('Pesquisa de Pauta de Sessão')


class ResumoOrdenacaoForm(forms.Form):
    primeiro = forms.ChoiceField(label=_('1°'),
                                 choices=ORDENACAO_RESUMO)
    segundo = forms.ChoiceField(label=_('2°'),
                                choices=ORDENACAO_RESUMO)
    terceiro = forms.ChoiceField(label='3°',
                                 choices=ORDENACAO_RESUMO)
    quarto = forms.ChoiceField(label=_('4°'),
                               choices=ORDENACAO_RESUMO)
    quinto = forms.ChoiceField(label=_('5°'),
                               choices=ORDENACAO_RESUMO)
    sexto = forms.ChoiceField(label=_('6°'),
                              choices=ORDENACAO_RESUMO)
    setimo = forms.ChoiceField(label=_('7°'),
                               choices=ORDENACAO_RESUMO)
    oitavo = forms.ChoiceField(label=_('8°'),
                               choices=ORDENACAO_RESUMO)
    nono = forms.ChoiceField(label=_('9°'),
                             choices=ORDENACAO_RESUMO)
    decimo = forms.ChoiceField(label='10°',
                               choices=ORDENACAO_RESUMO)

    def __init__(self, *args, **kwargs):
        super(ResumoOrdenacaoForm, self).__init__(*args, **kwargs)

        row1 = to_row(
            [('primeiro', 12)])
        row2 = to_row(
            [('segundo', 12)])
        row3 = to_row(
            [('terceiro', 12)])
        row4 = to_row(
            [('quarto', 12)])
        row5 = to_row(
            [('quinto', 12)])
        row6 = to_row(
            [('sexto', 12)])
        row7 = to_row(
            [('setimo', 12)])
        row8 = to_row(
            [('oitavo', 12)])
        row9 = to_row(
            [('nono', 12)])
        row10 = to_row(
            [('decimo', 12)])

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(_(''),
                     row1, row2, row3, row4, row5,
                     row6, row7, row8, row9, row10,
                     form_actions(label='Atualizar'))
        )

    def clean(self):
        super(ResumoOrdenacaoForm, self).clean()

        if not self.is_valid():
            return self.cleaned_data

        cleaned_data = self.cleaned_data

        for c1 in cleaned_data:
            i = 0
            for c2 in cleaned_data:
                if cleaned_data[str(c1)] == cleaned_data[str(c2)]:
                    i = i + 1
                    if i > 1:
                        raise ValidationError(_(
                            'Não é possível ter campos repetidos'))
        return self.cleaned_data
